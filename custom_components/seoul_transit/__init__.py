"""The Seoul Transit integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .api import SeoulTransitApiClient
from .const import (
    CONF_BUS_API_KEY,
    CONF_BUS_SCAN_INTERVAL,
    CONF_SUBWAY_API_KEY,
    CONF_SUBWAY_SCAN_INTERVAL,
    DEFAULT_BUS_SCAN_INTERVAL,
    DEFAULT_SUBWAY_SCAN_INTERVAL,
    DOMAIN,
    OLD_DEFAULT_SUBWAY_SCAN_INTERVAL,
    PLATFORMS,
    V2_DEFAULT_SUBWAY_SCAN_INTERVAL,
)


@dataclass
class SeoulTransitRuntimeData:
    """Runtime data for one Seoul Transit config entry."""

    client: SeoulTransitApiClient
    subway_coordinator: Any
    bus_coordinator: Any | None


async def async_setup_entry(hass: Any, entry: Any) -> bool:
    """Set up Seoul Transit from a config entry."""

    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from .coordinator import SeoulBusCoordinator, SeoulSubwayCoordinator

    session = async_get_clientsession(hass)
    client = SeoulTransitApiClient(
        session=session,
        subway_api_key=entry.data[CONF_SUBWAY_API_KEY],
        bus_api_key=entry.data.get(CONF_BUS_API_KEY),
    )
    subway_interval = entry.data.get(
        CONF_SUBWAY_SCAN_INTERVAL, DEFAULT_SUBWAY_SCAN_INTERVAL
    )
    subway_coordinator = SeoulSubwayCoordinator(hass, entry, client, subway_interval)
    bus_coordinator = None
    if entry.data.get(CONF_BUS_API_KEY):
        bus_interval = entry.data.get(CONF_BUS_SCAN_INTERVAL, DEFAULT_BUS_SCAN_INTERVAL)
        bus_coordinator = SeoulBusCoordinator(hass, entry, client, bus_interval)

    await subway_coordinator.async_config_entry_first_refresh()
    if bus_coordinator is not None:
        await bus_coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = SeoulTransitRuntimeData(
        client=client,
        subway_coordinator=subway_coordinator,
        bus_coordinator=bus_coordinator,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_migrate_entry(hass: Any, entry: Any) -> bool:
    """Migrate Seoul Transit config entries."""

    if entry.version < 3:
        data = dict(entry.data)
        previous_defaults = {
            OLD_DEFAULT_SUBWAY_SCAN_INTERVAL,
            V2_DEFAULT_SUBWAY_SCAN_INTERVAL,
        }
        if data.get(CONF_SUBWAY_SCAN_INTERVAL) in previous_defaults:
            data[CONF_SUBWAY_SCAN_INTERVAL] = DEFAULT_SUBWAY_SCAN_INTERVAL
        hass.config_entries.async_update_entry(entry, data=data, version=3)
    return True


async def async_unload_entry(hass: Any, entry: Any) -> bool:
    """Unload a Seoul Transit config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
