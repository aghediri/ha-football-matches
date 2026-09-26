"""Data update coordinator for Football Matches."""
from __future__ import annotations

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
    """Fetches fixtures from football-data.org for the configured competitions."""

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

    async def _async_update_data(self):
        """Fetch matches for today + the upcoming window across all competitions."""
        today = datetime.now(timezone.utc).date()
        date_from = today.isoformat()
        date_to = (today + timedelta(days=self._upcoming_days)).isoformat()
        comps = ",".join(COMPETITIONS.keys())
        url = (
            f"{API_BASE}/matches"
            f"?competitions={comps}&dateFrom={date_from}&dateTo={date_to}"
        )
        headers = {"X-Auth-Token": self._token}

        try:
            async with async_timeout.timeout(20):
                async with self._session.get(url, headers=headers) as resp:
                    if resp.status == 429:
                        raise UpdateFailed("Rate limited by football-data.org (429)")
                    if resp.status == 403:
                        raise UpdateFailed("Invalid API token (403)")
                    resp.raise_for_status()
                    data = await resp.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching matches: {err}") from err

        matches = data.get("matches", [])
        parsed = [self._parse_match(m) for m in matches]
        # sort by kickoff time
        parsed.sort(key=lambda m: m["utc_date"] or "")
        return self._organize(parsed, today)

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

    def _organize(self, matches: list[dict], today) -> dict:
        """Split matches into today, upcoming, per-league, and find the next one."""
        today_matches = []
        upcoming = []
        now = datetime.now(timezone.utc)
        next_match = None

        for m in matches:
            if not m["utc_date"]:
                continue
            kickoff = datetime.fromisoformat(m["utc_date"].replace("Z", "+00:00"))
            m["kickoff_local"] = kickoff.isoformat()
            if kickoff.date() == today:
                today_matches.append(m)
            else:
                upcoming.append(m)
            # next match = first not-yet-finished fixture in the future
            if next_match is None and kickoff >= now and m["status"] in (
                "SCHEDULED", "TIMED", "IN_PLAY", "PAUSED",
            ):
                next_match = m

        per_league = {code: [] for code in COMPETITIONS}
        for m in matches:
            code = m.get("competition_code")
            if code in per_league:
                per_league[code].append(m)

        return {
            "today": today_matches,
            "upcoming": upcoming,
            "all": matches,
            "per_league": per_league,
            "next_match": next_match,
        }
