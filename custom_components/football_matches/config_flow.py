"""Config flow for Football Matches."""
from __future__ import annotations

import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_BASE,
    CONF_API_TOKEN,
    CONF_LIVE_API_TOKEN,
    CONF_UPCOMING_DAYS,
    DEFAULT_UPCOMING_DAYS,
    DOMAIN,
)


async def _validate_token(hass, token: str) -> bool:
    session = async_get_clientsession(hass)
    try:
        async with async_timeout.timeout(15):
            async with session.get(
                f"{API_BASE}/competitions/PL",
                headers={"X-Auth-Token": token},
            ) as resp:
                return resp.status == 200
    except (aiohttp.ClientError, TimeoutError):
        return False


async def _validate_live_token(hass, token: str) -> bool:
    """Verify an API-Football key (optional)."""
    if not token:
        return True
    session = async_get_clientsession(hass)
    try:
        async with async_timeout.timeout(15):
            async with session.get(
                "https://v3.football.api-sports.io/status",
                headers={"x-apisports-key": token},
            ) as resp:
                return resp.status == 200
    except (aiohttp.ClientError, TimeoutError):
        return False


class FootballConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            token = user_input[CONF_API_TOKEN].strip()
            live_token = user_input.get(CONF_LIVE_API_TOKEN, "").strip()
            if not await _validate_token(self.hass, token):
                errors["base"] = "invalid_auth"
            elif live_token and not await _validate_live_token(self.hass, live_token):
                errors["base"] = "invalid_live_auth"
            else:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Football Matches",
                    data={
                        CONF_API_TOKEN: token,
                        CONF_LIVE_API_TOKEN: live_token,
                        CONF_UPCOMING_DAYS: user_input.get(
                            CONF_UPCOMING_DAYS, DEFAULT_UPCOMING_DAYS
                        ),
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_API_TOKEN): str,
                vol.Optional(CONF_LIVE_API_TOKEN, default=""): str,
                vol.Optional(
                    CONF_UPCOMING_DAYS, default=DEFAULT_UPCOMING_DAYS
                ): vol.All(int, vol.Range(min=1, max=30)),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return FootballOptionsFlow(config_entry)


class FootballOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data = self.config_entry.data
        opts = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_UPCOMING_DAYS,
                    default=opts.get(CONF_UPCOMING_DAYS, data.get(CONF_UPCOMING_DAYS, DEFAULT_UPCOMING_DAYS)),
                ): vol.All(int, vol.Range(min=1, max=30)),
                vol.Optional(
                    CONF_LIVE_API_TOKEN,
                    default=opts.get(CONF_LIVE_API_TOKEN, data.get(CONF_LIVE_API_TOKEN, "")),
                ): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
