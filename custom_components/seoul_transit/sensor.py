"""Sensor platform for Seoul Transit."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTime
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SUBWAY_LINES
from .models import (
    Arrival,
    SensorSpec,
    build_sensor_specs,
    native_minutes,
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
        self._attr_name = spec.label
        self._attr_unique_id = unique_id_for_sensor(spec.key)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "gunja_2012")},
            name="Seoul Transit",
            manufacturer="Seoul Metropolitan Government",
            entry_type=DeviceEntryType.SERVICE,
        )

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
                    "station": arrival.station_name if arrival else "군자(능동)",
                    "line": arrival.line_name
                    if arrival
                    else SUBWAY_LINES.get(self._spec.line_id or ""),
                    "line_id": self._spec.line_id,
                    "direction": self._spec.direction,
                }
            )
        if arrival is None:
            return {key: value for key, value in attrs.items() if value is not None}

        attrs.update(
            {
                "raw_message": arrival.raw_message,
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
        return {key: value for key, value in attrs.items() if value is not None}

    @property
    def _arrival(self) -> Arrival | None:
        return (self.coordinator.data or {}).get(self._spec.key)
