"""Sensor platform for Football Matches."""
from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COMPETITIONS, DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        TodayMatchesSensor(coordinator, entry),
        UpcomingMatchesSensor(coordinator, entry),
        NextMatchSensor(coordinator, entry),
    ]
    for code, name in COMPETITIONS.items():
        entities.append(LeagueSensor(coordinator, entry, code, name))
    async_add_entities(entities)


class _Base(CoordinatorEntity, SensorEntity):
    """Shared device + coordinator wiring."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="Football Matches",
            manufacturer="football-data.org",
            model="European Leagues",
        )


class TodayMatchesSensor(_Base):
    """Number of matches today, with the full list in attributes."""

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
        return {"matches": self.coordinator.data.get("today", [])}


class UpcomingMatchesSensor(_Base):
    """Number of upcoming matches in the window, list in attributes."""

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
    """The next upcoming fixture; state = a readable summary, plus countdown."""

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
        # add a minutes-until countdown
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
    """Per-competition sensor: count + matches list."""

    _attr_icon = "mdi:trophy"

    def __init__(self, coordinator, entry, code, name):
        super().__init__(coordinator, entry)
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
        return {"competition_code": self._code, "matches": matches}
