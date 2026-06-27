"""Data update coordinators for Seoul Transit."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    SeoulTransitApiClient,
    SeoulTransitAuthError,
    SeoulTransitConnectionError,
)
from .const import DOMAIN, SUBWAY_DIRECTIONS, SUBWAY_LINES
from .models import Arrival, subway_sensor_key

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
            raise UpdateFailed(f"Error communicating with Seoul subway API: {err}") from err

        data: dict[str, Arrival | None] = {}
        for line_id in SUBWAY_LINES:
            for direction in SUBWAY_DIRECTIONS:
                key = subway_sensor_key(line_id, direction)
                values = arrivals.get((line_id, direction), [])
                data[key] = values[0] if values else None
                if values[1:]:
                    second = values[1]
                    current = data[key]
                    if current is not None:
                        current.attributes["second_arrival_minutes"] = second.minutes
                        current.attributes["second_arrival_message"] = second.raw_message
                        current.attributes["second_destination"] = second.destination
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
            raise UpdateFailed(f"Error communicating with Seoul bus API: {err}") from err

