"""Config flow for Seoul Transit."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
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
            vol.Required(
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

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""

        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id("gunja_2012")
            self._abort_if_unique_id_configured()
            try:
                await self._async_validate_input(user_input)
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

    async def _async_validate_input(self, user_input: dict[str, Any]) -> None:
        """Validate API keys by requesting the configured v1 endpoints."""

        session = async_get_clientsession(self.hass)
        client = SeoulTransitApiClient(
            session=session,
            subway_api_key=user_input[CONF_SUBWAY_API_KEY],
            bus_api_key=user_input[CONF_BUS_API_KEY],
        )
        await client.async_fetch_subway()
        await client.async_fetch_bus()

