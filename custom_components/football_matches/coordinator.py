"""Data update coordinator for Football Matches."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import aiohttp
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import API_BASE, COMPETITIONS

_LOGGER = logging.getLogger(__name__)


class FootballCoordinator(DataUpdateCoordinator):
    """Fetches fixtures from football-data.org, one competition at a time.

    The free tier restricts multi-competition + wide date-range queries, so we
    query each competition individually using status=SCHEDULED (which the free
    tier serves reliably) and filter to the upcoming window client-side.
    """

    def __init__(self, hass: HomeAssistant, api_token: str, upcoming_days: int, scan_minutes: int):
        super().__init__(
            hass,
            _LOGGER,
            name="football_matches",
            update_interval=timedelta(minutes=scan_minutes),
        )
        self._token = api_token
        self._upcoming_days = upcoming_days
        self._session = async_get_clientsession(hass)

    async def _fetch_competition(self, code: str) -> list[dict]:
        """Fetch scheduled + in-play + recently finished matches for one competition."""
        url = f"{API_BASE}/competitions/{code}/matches"
        headers = {"X-Auth-Token": self._token}
        try:
            async with async_timeout.timeout(20):
                async with self._session.get(url, headers=headers) as resp:
                    if resp.status == 429:
                        _LOGGER.warning("Rate limited on %s (429)", code)
                        return []
                    if resp.status in (403, 400):
                        _LOGGER.warning("Competition %s not available (%s)", code, resp.status)
                        return []
                    resp.raise_for_status()
                    data = await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.warning("Error fetching %s: %s", code, err)
            return []
        return data.get("matches", [])

    async def _async_update_data(self):
        """Fetch all competitions individually and merge."""
        results = await asyncio.gather(
            *[self._fetch_competition(code) for code in COMPETITIONS],
            return_exceptions=True,
        )
        raw = []
        for res in results:
            if isinstance(res, list):
                raw.extend(res)

        if not raw:
            # Not necessarily an error — could be off-season/international break.
            _LOGGER.debug("No matches returned across competitions")

        parsed = [self._parse_match(m) for m in raw]
        parsed.sort(key=lambda m: m["utc_date"] or "")
        return self._organize(parsed)

    @staticmethod
    def _parse_match(m: dict) -> dict:
        comp = m.get("competition", {})
        home = m.get("homeTeam", {})
        away = m.get("awayTeam", {})
        score = m.get("score", {}).get("fullTime", {})
        return {
            "id": m.get("id"),
            "competition_code": comp.get("code"),
            "competition": comp.get("name"),
            "competition_emblem": comp.get("emblem"),
            "utc_date": m.get("utcDate"),
            "status": m.get("status"),
            "matchday": m.get("matchday"),
            "home": home.get("name"),
            "home_crest": home.get("crest"),
            "away": away.get("name"),
            "away_crest": away.get("crest"),
            "home_score": score.get("home"),
            "away_score": score.get("away"),
        }

    def _organize(self, matches: list[dict]) -> dict:
        """Split into today, upcoming window, per-league, next match."""
        now = datetime.now(timezone.utc)
        today = now.date()
        window_end = today + timedelta(days=self._upcoming_days)

        today_matches, upcoming, next_match = [], [], None
        per_league = {code: [] for code in COMPETITIONS}

        for m in matches:
            if not m["utc_date"]:
                continue
            try:
                kickoff = datetime.fromisoformat(m["utc_date"].replace("Z", "+00:00"))
            except ValueError:
                continue
            m["kickoff_local"] = kickoff.isoformat()
            kdate = kickoff.date()

            # today's fixtures
            if kdate == today:
                today_matches.append(m)
            # upcoming within window (future, excluding today)
            elif today < kdate <= window_end:
                upcoming.append(m)

            # per-league: today + upcoming window only (keeps attrs small)
            if today <= kdate <= window_end:
                code = m.get("competition_code")
                if code in per_league:
                    per_league[code].append(m)

            # next match = earliest future not-yet-finished fixture
            if (
                next_match is None
                and kickoff >= now
                and m["status"] in ("SCHEDULED", "TIMED", "IN_PLAY", "PAUSED")
            ):
                next_match = m

        # If nothing in the window, still surface the very next fixture overall
        if next_match is None:
            future = [
                m for m in matches
                if m["utc_date"]
                and datetime.fromisoformat(m["utc_date"].replace("Z", "+00:00")) >= now
            ]
            if future:
                next_match = future[0]

        return {
            "today": today_matches,
            "upcoming": upcoming,
            "all": matches,
            "per_league": per_league,
            "next_match": next_match,
        }
