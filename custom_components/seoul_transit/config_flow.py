"""Config flow for Seoul Transit."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    SeoulTransitApiClient,
    SeoulTransitAuthError,
    SeoulTransitConnectionError,
)
from .const import (
    CONF_BUS_API_KEY,
    CONF_BUS_SCAN_INTERVAL,
    CONF_SUBWAY_API_KEY,
    CONF_SUBWAY_SCAN_INTERVAL,
    DEFAULT_BUS_SCAN_INTERVAL,
    DEFAULT_SUBWAY_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_SUBWAY_API_KEY,
                default=defaults.get(CONF_SUBWAY_API_KEY, ""),
            ): str,
            vol.Optional(
                CONF_BUS_API_KEY,
                default=defaults.get(CONF_BUS_API_KEY, ""),
            ): str,
            vol.Optional(
                CONF_SUBWAY_SCAN_INTERVAL,
                default=defaults.get(
                    CONF_SUBWAY_SCAN_INTERVAL, DEFAULT_SUBWAY_SCAN_INTERVAL
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)),
            vol.Optional(
                CONF_BUS_SCAN_INTERVAL,
                default=defaults.get(CONF_BUS_SCAN_INTERVAL, DEFAULT_BUS_SCAN_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)),
        }
    )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Seoul Transit."""

    VERSION = 3

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow handler."""

        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""

        errors: dict[str, str] = {}
        if user_input is not None:
            user_input = _normalize_user_input(user_input)
            await self.async_set_unique_id("gunja_2012")
            self._abort_if_unique_id_configured()
            try:
                await _async_validate_input(self.hass, user_input)
            except SeoulTransitAuthError:
                errors["base"] = "invalid_auth"
            except SeoulTransitConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="Seoul Transit", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input),
            errors=errors,
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Seoul Transit options updates."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage Seoul Transit options."""

        defaults = {**self._config_entry.data, **self._config_entry.options}
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input = _normalize_user_input(user_input)
            try:
                await _async_validate_input(self.hass, user_input)
            except SeoulTransitAuthError:
                errors["base"] = "invalid_auth"
            except SeoulTransitConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(user_input or defaults),
            errors=errors,
        )


async def _async_validate_input(hass: Any, user_input: dict[str, Any]) -> None:
    """Validate API keys by requesting the configured v1 endpoints."""

    if not user_input.get(CONF_SUBWAY_API_KEY):
        raise SeoulTransitAuthError("Missing subway API key")

    session = async_get_clientsession(hass)
    client = SeoulTransitApiClient(
        session=session,
        subway_api_key=user_input[CONF_SUBWAY_API_KEY],
        bus_api_key=user_input.get(CONF_BUS_API_KEY),
    )
    await client.async_fetch_subway()
    if user_input.get(CONF_BUS_API_KEY):
        await client.async_fetch_bus()


def _normalize_user_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Return config flow data with whitespace-only optional keys removed."""

    data = dict(user_input)
    for key in (CONF_SUBWAY_API_KEY, CONF_BUS_API_KEY):
        if key in data and isinstance(data[key], str):
            data[key] = data[key].strip()
    if not data.get(CONF_BUS_API_KEY):
        data.pop(CONF_BUS_API_KEY, None)
    return data
