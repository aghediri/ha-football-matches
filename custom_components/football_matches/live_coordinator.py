"""Live-score coordinator (API-Football) — polls only during in-play windows."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import aiohttp
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .team_aliases import match_key

_LOGGER = logging.getLogger(__name__)

API_FOOTBALL_URL = "https://v3.football.api-sports.io/fixtures?live=all"
LIVE_WINDOW_HOURS = 2.5      # poll-eligible window after kickoff
LIVE_POLL_MINUTES = 3        # poll interval while inside a live window
DAILY_CALL_CAP = 90         # stay safely under free 100/day

# API-Football league IDs for our competitions
AF_LEAGUE_IDS = {39: "PL", 61: "FL1", 140: "PD", 135: "SA", 2: "CL"}


class LiveScoreCoordinator(DataUpdateCoordinator):
    """Polls API-Football live endpoint ONLY when a fixture is in its live window."""

    def __init__(self, hass: HomeAssistant, api_token: str, fixtures_coordinator):
        super().__init__(
            hass, _LOGGER, name="football_live",
            update_interval=timedelta(minutes=LIVE_POLL_MINUTES),
        )
        self._token = api_token
        self._fixtures = fixtures_coordinator
        self._session = async_get_clientsession(hass)
        self._calls_today = 0
        self._call_day = datetime.now(timezone.utc).date()

    def _in_live_window(self) -> bool:
        now = datetime.now(timezone.utc)
        data = self._fixtures.data or {}
        for m in data.get("all", []):
            if not m.get("utc_date"):
                continue
            try:
                k = datetime.fromisoformat(m["utc_date"].replace("Z", "+00:00"))
            except ValueError:
                continue
            if k <= now <= k + timedelta(hours=LIVE_WINDOW_HOURS):
                return True
        return False

    def _reset_cap_if_new_day(self):
        today = datetime.now(timezone.utc).date()
        if today != self._call_day:
            self._call_day = today
            self._calls_today = 0

    async def _async_update_data(self):
        self._reset_cap_if_new_day()

        if not self._in_live_window():
            return {"live": {}, "polling": False, "calls_today": self._calls_today}
        if self._calls_today >= DAILY_CALL_CAP:
            _LOGGER.warning("Live-score daily cap reached (%s)", DAILY_CALL_CAP)
            return {"live": {}, "polling": False, "calls_today": self._calls_today, "capped": True}

        try:
            async with async_timeout.timeout(20):
                async with self._session.get(
                    API_FOOTBALL_URL, headers={"x-apisports-key": self._token}
                ) as resp:
                    self._calls_today += 1
                    if resp.status == 429:
                        _LOGGER.warning("API-Football rate limited (429)")
                        return {"live": {}, "polling": True, "calls_today": self._calls_today}
                    resp.raise_for_status()
                    data = await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.warning("Live fetch error: %s", err)
            return {"live": {}, "polling": True, "calls_today": self._calls_today}

        # Build canonical-key -> live info, using the SAME normalization as fixtures
        live = {}
        for f in data.get("response", []):
            league_id = f.get("league", {}).get("id")
            if league_id not in AF_LEAGUE_IDS:
                continue
            teams = f.get("teams", {})
            goals = f.get("goals", {})
            status = f.get("fixture", {}).get("status", {})
            key = match_key(
                teams.get("home", {}).get("name", ""),
                teams.get("away", {}).get("name", ""),
            )
            live[key] = {
                "home_score": goals.get("home"),
                "away_score": goals.get("away"),
                "minute": status.get("elapsed"),
                "status_short": status.get("short"),
                "league": AF_LEAGUE_IDS[league_id],
            }
        return {"live": live, "polling": True, "calls_today": self._calls_today}
