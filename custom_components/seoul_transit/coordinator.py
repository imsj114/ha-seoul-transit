"""Data update coordinators for Seoul Transit."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import timedelta
from typing import Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    SeoulTransitApiClient,
    SeoulTransitAuthError,
    SeoulTransitConnectionError,
)
from .const import DOMAIN
from .models import Arrival, build_sensor_specs

_LOGGER = logging.getLogger(__name__)


class SeoulSubwayCoordinator(DataUpdateCoordinator[dict[str, Arrival | None]]):
    """Coordinator for realtime subway arrivals."""

    def __init__(
        self,
        hass: Any,
        config_entry: Any,
        client: SeoulTransitApiClient,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_subway",
            config_entry=config_entry,
            update_interval=timedelta(seconds=scan_interval),
            always_update=False,
        )
        self._client = client

    async def _async_update_data(self) -> dict[str, Arrival | None]:
        try:
            arrivals = await self._client.async_fetch_subway()
        except SeoulTransitAuthError as err:
            raise ConfigEntryAuthFailed from err
        except SeoulTransitConnectionError as err:
            raise UpdateFailed(
                f"Error communicating with Seoul subway API: {err}"
            ) from err

        data: dict[str, Arrival | None] = {}
        for spec in build_sensor_specs(include_bus=False):
            values = arrivals.get(spec.key, [])
            if not values:
                data[spec.key] = None
                continue
            data[spec.key] = replace(values[0], following=tuple(values[1:]))
        return data


class SeoulBusCoordinator(DataUpdateCoordinator[dict[str, Arrival | None]]):
    """Coordinator for realtime bus arrivals."""

    def __init__(
        self,
        hass: Any,
        config_entry: Any,
        client: SeoulTransitApiClient,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_bus",
            config_entry=config_entry,
            update_interval=timedelta(seconds=scan_interval),
            always_update=False,
        )
        self._client = client

    async def _async_update_data(self) -> dict[str, Arrival | None]:
        try:
            return await self._client.async_fetch_bus()
        except SeoulTransitAuthError as err:
            raise ConfigEntryAuthFailed from err
        except SeoulTransitConnectionError as err:
            raise UpdateFailed(
                f"Error communicating with Seoul bus API: {err}"
            ) from err
