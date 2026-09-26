"""The Football Matches integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_API_TOKEN,
    CONF_LIVE_API_TOKEN,
    CONF_UPCOMING_DAYS,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DEFAULT_UPCOMING_DAYS,
    DOMAIN,
)
from .coordinator import FootballCoordinator
from .live_coordinator import LiveScoreCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Football Matches from a config entry."""
    token = entry.data[CONF_API_TOKEN]
    upcoming_days = entry.options.get(
        CONF_UPCOMING_DAYS, entry.data.get(CONF_UPCOMING_DAYS, DEFAULT_UPCOMING_DAYS)
    )
    coordinator = FootballCoordinator(
        hass, token, upcoming_days, DEFAULT_SCAN_INTERVAL_MINUTES
    )
    await coordinator.async_config_entry_first_refresh()

    # Optional live-score coordinator (API-Football) — only if a live token is set
    live_coordinator = None
    live_token = entry.options.get(
        CONF_LIVE_API_TOKEN, entry.data.get(CONF_LIVE_API_TOKEN, "")
    )
    if live_token:
        live_coordinator = LiveScoreCoordinator(hass, live_token, coordinator)
        await live_coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "fixtures": coordinator,
        "live": live_coordinator,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
