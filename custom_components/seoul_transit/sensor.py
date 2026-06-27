"""Sensor platform for Seoul Transit."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTime
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SUBWAY_LINE_NAMES
from .models import (
    Arrival,
    SensorSpec,
    build_sensor_specs,
    native_minutes,
    next_minute_change_delay,
    unique_id_for_sensor,
)


async def async_setup_entry(
    hass: Any,
    entry: Any,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Seoul Transit sensors from a config entry."""

    runtime = hass.data[DOMAIN][entry.entry_id]
    entities: list[SeoulTransitArrivalSensor] = []
    for spec in build_sensor_specs(include_bus=runtime.bus_coordinator is not None):
        coordinator = (
            runtime.subway_coordinator
            if spec.source == "subway"
            else runtime.bus_coordinator
        )
        entities.append(SeoulTransitArrivalSensor(coordinator, spec))
    async_add_entities(entities)


class SeoulTransitArrivalSensor(CoordinatorEntity, SensorEntity):
    """Next-arrival sensor backed by a Seoul Transit coordinator."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(self, coordinator: Any, spec: SensorSpec) -> None:
        super().__init__(coordinator)
        self._spec = spec
        self._cancel_local_countdown_update: Callable[[], None] | None = None
        self._attr_name = spec.label
        self._attr_unique_id = unique_id_for_sensor(spec.key)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "gunja_2012")},
            name="Seoul Transit",
            manufacturer="Seoul Metropolitan Government",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        """Start local countdown updates between API refreshes."""

        await super().async_added_to_hass()
        self.async_on_remove(self._cancel_scheduled_local_countdown_update)
        self._schedule_local_countdown_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle new API data and reschedule local countdown updates."""

        super()._handle_coordinator_update()
        self._schedule_local_countdown_update()

    @callback
    def _async_handle_local_countdown_update(self, _now: datetime) -> None:
        """Refresh the HA state without making an API request."""

        self._cancel_local_countdown_update = None
        if self._arrival is not None and self._arrival.estimated_arrival_at is not None:
            self.async_write_ha_state()
        self._schedule_local_countdown_update()

    @callback
    def _schedule_local_countdown_update(self) -> None:
        """Schedule the next local update when the minute value should change."""

        self._cancel_scheduled_local_countdown_update()
        delay = next_minute_change_delay(self._arrival)
        if delay is None:
            return
        self._cancel_local_countdown_update = async_call_later(
            self.hass,
            delay,
            self._async_handle_local_countdown_update,
        )

    @callback
    def _cancel_scheduled_local_countdown_update(self) -> None:
        """Cancel the current local countdown timer, if one is pending."""

        if self._cancel_local_countdown_update is None:
            return
        self._cancel_local_countdown_update()
        self._cancel_local_countdown_update = None

    @property
    def native_value(self) -> int | None:
        """Return minutes until the next arrival."""

        return native_minutes(self._arrival)

    @property
    def available(self) -> bool:
        """Return whether the API coordinator is currently available."""

        return super().available

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional arrival details."""

        arrival = self._arrival
        attrs: dict[str, Any] = {
            "source": self._spec.source,
            "raw_message": None,
        }
        if self._spec.source == "subway":
            attrs.update(
                {
                    "station": (
                        arrival.station_name if arrival else self._spec.station_name
                    ),
                    "station_key": self._spec.station_key,
                    "line": arrival.line_name
                    if arrival
                    else SUBWAY_LINE_NAMES.get(self._spec.line_id or ""),
                    "line_id": self._spec.line_id,
                    "direction": self._spec.direction,
                }
            )
        if arrival is None:
            return {key: value for key, value in attrs.items() if value is not None}

        attrs.update(
            {
                "raw_message": arrival.raw_message,
                "api_remaining_minutes": arrival.minutes,
                "api_remaining_seconds": arrival.remaining_seconds,
                "received_at": _isoformat(arrival.received_at),
                "estimated_arrival_at": _isoformat(arrival.estimated_arrival_at),
                "destination": arrival.destination,
                "current_location": arrival.current_location,
                "generated_at": arrival.generated_at,
                "vehicle_id": arrival.vehicle_id,
                "route": arrival.route_name,
                "route_id": arrival.route_id,
                "stop": arrival.stop_name,
                "stop_id": arrival.stop_id,
                "ars_id": arrival.ars_id,
            }
        )
        attrs.update(arrival.attributes)
        return {
            key: _isoformat(value) if isinstance(value, datetime) else value
            for key, value in attrs.items()
            if value is not None
        }

    @property
    def _arrival(self) -> Arrival | None:
        return (self.coordinator.data or {}).get(self._spec.key)


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
