"""Sensor platform for Football Matches."""
from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COMPETITIONS, DOMAIN
from .team_aliases import match_key


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up sensors from a config entry."""
    store = hass.data[DOMAIN][entry.entry_id]
    coordinator = store["fixtures"]
    live = store.get("live")

    entities = [
        TodayMatchesSensor(coordinator, entry, live),
        UpcomingMatchesSensor(coordinator, entry, live),
        NextMatchSensor(coordinator, entry, live),
    ]
    for code, name in COMPETITIONS.items():
        entities.append(LeagueSensor(coordinator, entry, code, name, live))
    if live is not None:
        entities.append(LiveScoresSensor(live, coordinator, entry))
    async_add_entities(entities)


def _merge_live(matches, live_data):
    """Return a copy of matches with live score/minute merged in where available."""
    if not live_data:
        return matches
    live = live_data.get("live", {})
    if not live:
        return matches
    out = []
    for m in matches:
        mm = dict(m)
        key = match_key(m.get("home", ""), m.get("away", ""))
        if key in live:
            lv = live[key]
            mm["home_score"] = lv.get("home_score", mm.get("home_score"))
            mm["away_score"] = lv.get("away_score", mm.get("away_score"))
            mm["minute"] = lv.get("minute")
            mm["live_status"] = lv.get("status_short")
            mm["is_live"] = lv.get("status_short") in ("1H", "2H", "ET", "LIVE", "HT", "P", "BT")
        out.append(mm)
    return out


class _Base(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, live=None):
        super().__init__(coordinator)
        self._entry = entry
        self._live = live

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="Football Matches",
            manufacturer="football-data.org",
            model="European Leagues",
        )


class TodayMatchesSensor(_Base):
    _attr_icon = "mdi:soccer"
    _attr_name = "Today"

    @property
    def unique_id(self):
        return f"{self._entry.entry_id}_today"

    @property
    def native_value(self):
        return len(self.coordinator.data.get("today", []))

    @property
    def extra_state_attributes(self):
        ld = self._live.data if self._live else None
        return {"matches": _merge_live(self.coordinator.data.get("today", []), ld)}


class UpcomingMatchesSensor(_Base):
    _attr_icon = "mdi:calendar-clock"
    _attr_name = "Upcoming"

    @property
    def unique_id(self):
        return f"{self._entry.entry_id}_upcoming"

    @property
    def native_value(self):
        return len(self.coordinator.data.get("upcoming", []))

    @property
    def extra_state_attributes(self):
        return {"matches": self.coordinator.data.get("upcoming", [])}


class NextMatchSensor(_Base):
    _attr_icon = "mdi:soccer-field"
    _attr_name = "Next Match"

    @property
    def unique_id(self):
        return f"{self._entry.entry_id}_next"

    @property
    def native_value(self):
        m = self.coordinator.data.get("next_match")
        if not m:
            return "No upcoming match"
        return f"{m['home']} vs {m['away']}"

    @property
    def extra_state_attributes(self):
        m = self.coordinator.data.get("next_match")
        if not m:
            return {}
        attrs = dict(m)
        try:
            kickoff = datetime.fromisoformat(m["utc_date"].replace("Z", "+00:00"))
            delta = kickoff - datetime.now(timezone.utc)
            mins = int(delta.total_seconds() // 60)
            attrs["minutes_until"] = mins
            attrs["hours_until"] = round(mins / 60, 1)
        except (ValueError, AttributeError, TypeError):
            pass
        return attrs


class LeagueSensor(_Base):
    _attr_icon = "mdi:trophy"

    def __init__(self, coordinator, entry, code, name, live=None):
        super().__init__(coordinator, entry, live)
        self._code = code
        self._attr_name = name

    @property
    def unique_id(self):
        return f"{self._entry.entry_id}_{self._code}"

    @property
    def native_value(self):
        return len(self.coordinator.data.get("per_league", {}).get(self._code, []))

    @property
    def extra_state_attributes(self):
        matches = self.coordinator.data.get("per_league", {}).get(self._code, [])
        ld = self._live.data if self._live else None
        return {"competition_code": self._code, "matches": _merge_live(matches, ld)}


class LiveScoresSensor(CoordinatorEntity, SensorEntity):
    """Number of matches currently live, with details in attributes."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:soccer"
    _attr_name = "Live Scores"

    def __init__(self, live_coordinator, fixtures_coordinator, entry):
        super().__init__(live_coordinator)
        self._entry = entry
        self._fixtures = fixtures_coordinator

    @property
    def unique_id(self):
        return f"{self._entry.entry_id}_live"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(identifiers={(DOMAIN, self._entry.entry_id)}, name="Football Matches")

    @property
    def native_value(self):
        return len((self.coordinator.data or {}).get("live", {}))

    @property
    def extra_state_attributes(self):
        d = self.coordinator.data or {}
        return {
            "polling": d.get("polling", False),
            "calls_today": d.get("calls_today", 0),
            "live": d.get("live", {}),
        }
