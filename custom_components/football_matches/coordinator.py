"""Data update coordinator for Football Matches."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import aiohttp
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import API_BASE, COMPETITIONS

_LOGGER = logging.getLogger(__name__)

# How many upcoming fixtures to keep per league (independent of the today/upcoming window)
PER_LEAGUE_LIMIT = 15


class FootballCoordinator(DataUpdateCoordinator):
    """Fetches fixtures per-competition (free-tier friendly)."""

    def __init__(self, hass, api_token, upcoming_days, scan_minutes):
        super().__init__(hass, _LOGGER, name="football_matches",
                         update_interval=timedelta(minutes=scan_minutes))
        self._token = api_token
        self._upcoming_days = upcoming_days
        self._session = async_get_clientsession(hass)

    async def _fetch_competition(self, code):
        # Date-range fetch (NOT status=SCHEDULED): includes recently FINISHED
        # matches (final scores), today's/IN_PLAY matches, and upcoming fixtures.
        # A status=SCHEDULED query drops a match the moment it kicks off/finishes,
        # which hid today's games and all scores.
        from datetime import date, timedelta
        date_from = (date.today() - timedelta(days=3)).isoformat()  # keep 3 days of past results
        date_to = (date.today() + timedelta(days=self._upcoming_days + 7)).isoformat()
        url = (f"{API_BASE}/competitions/{code}/matches"
               f"?dateFrom={date_from}&dateTo={date_to}")
        headers = {"X-Auth-Token": self._token}
        try:
            async with async_timeout.timeout(20):
                async with self._session.get(url, headers=headers) as resp:
                    if resp.status in (429, 403, 400):
                        _LOGGER.warning("Comp %s unavailable (%s)", code, resp.status)
                        return []
                    resp.raise_for_status()
                    data = await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.warning("Error fetching %s: %s", code, err)
            return []
        return data.get("matches", [])

    async def _async_update_data(self):
        results = await asyncio.gather(
            *[self._fetch_competition(c) for c in COMPETITIONS],
            return_exceptions=True)
        raw = []
        for res in results:
            if isinstance(res, list):
                raw.extend(res)
        parsed = [self._parse_match(m) for m in raw]
        parsed.sort(key=lambda m: m["utc_date"] or "")
        return self._organize(parsed)

    @staticmethod
    def _parse_match(m):
        comp = m.get("competition", {}); home = m.get("homeTeam", {})
        away = m.get("awayTeam", {}); score = m.get("score", {}).get("fullTime", {})
        return {"id": m.get("id"), "competition_code": comp.get("code"),
                "competition": comp.get("name"), "competition_emblem": comp.get("emblem"),
                "utc_date": m.get("utcDate"), "status": m.get("status"),
                "matchday": m.get("matchday"), "home": home.get("name"),
                "home_crest": home.get("crest"), "away": away.get("name"),
                "away_crest": away.get("crest"), "home_score": score.get("home"),
                "away_score": score.get("away")}

    def _organize(self, matches):
        now = datetime.now(timezone.utc); today = now.date()
        window_end = today + timedelta(days=self._upcoming_days)
        today_m, upcoming, next_match = [], [], None
        # per-league: keep the FULL upcoming list (future fixtures), capped
        per_league = {c: [] for c in COMPETITIONS}

        for m in matches:
            if not m["utc_date"]:
                continue
            try:
                k = datetime.fromisoformat(m["utc_date"].replace("Z", "+00:00"))
            except ValueError:
                continue
            m["kickoff_local"] = k.isoformat(); kd = k.date()

            if kd == today:
                today_m.append(m)
            elif today < kd <= window_end:
                upcoming.append(m)

            # per-league = recent past (last 3 days, for score look-back) + today + future
            if k >= (now - timedelta(days=3)):
                c = m.get("competition_code")
                if c in per_league and len(per_league[c]) < PER_LEAGUE_LIMIT:
                    per_league[c].append(m)

            if (next_match is None and k >= now and
                    m["status"] in ("SCHEDULED", "TIMED", "IN_PLAY", "PAUSED")):
                next_match = m

        if next_match is None:
            fut = [m for m in matches if m["utc_date"] and
                   datetime.fromisoformat(m["utc_date"].replace("Z", "+00:00")) >= now]
            if fut:
                next_match = fut[0]

        return {"today": today_m, "upcoming": upcoming, "all": matches,
                "per_league": per_league, "next_match": next_match}
