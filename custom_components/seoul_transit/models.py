"""Pure data models shared by the Seoul Transit integration and tests."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .const import (
    BUS_STOPS,
    DOMAIN,
    SUBWAY_DIRECTIONS,
    SUBWAY_LINE_KEYS,
    SUBWAY_LINE_NAMES,
    SUBWAY_STOPS,
)

COUNTDOWN_CHANGE_DELAY_SECONDS = 0.1


@dataclass(frozen=True)
class Arrival:
    """A normalized transit arrival."""

    minutes: int | None
    raw_message: str | None
    remaining_seconds: int | None = None
    received_at: datetime | None = None
    estimated_arrival_at: datetime | None = None
    destination: str | None = None
    current_location: str | None = None
    generated_at: str | None = None
    vehicle_id: str | None = None
    line_id: str | None = None
    line_name: str | None = None
    direction: str | None = None
    station_name: str | None = None
    stop_name: str | None = None
    stop_id: str | None = None
    ars_id: str | None = None
    route_id: str | None = None
    route_name: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SensorSpec:
    """Description of one v1 Home Assistant sensor."""

    key: str
    label: str
    source: str
    station_key: str | None = None
    station_name: str | None = None
    line_id: str | None = None
    direction: str | None = None
    stop_key: str | None = None


def subway_sensor_key(line_id: str, direction: str, station_key: str = "gunja") -> str:
    """Return the stable sensor key for a subway line/direction pair."""

    direction_key = "up" if direction == "상행" else "down"
    line_key = SUBWAY_LINE_KEYS[line_id]
    if station_key == "gunja":
        return f"subway_line_{line_key}_{direction_key}"
    return f"subway_{station_key}_line_{line_key}_{direction_key}"


def build_sensor_specs(include_bus: bool = True) -> tuple[SensorSpec, ...]:
    """Return the complete fixed v1 sensor set."""

    subway_specs = tuple(
        SensorSpec(
            key=subway_sensor_key(line_id, direction, stop.key),
            label=f"{stop.label} {line_name} {direction}",
            source="subway",
            station_key=stop.key,
            station_name=stop.name,
            line_id=line_id,
            direction=direction,
        )
        for stop in SUBWAY_STOPS
        for line_id in stop.line_ids
        for line_name in (SUBWAY_LINE_NAMES[line_id],)
        for direction in SUBWAY_DIRECTIONS
    )
    if not include_bus:
        return subway_specs

    bus_specs = tuple(
        SensorSpec(
            key=stop.key,
            label=f"{stop.route_name} {stop.name} {stop.ars_id}",
            source="bus",
            stop_key=stop.key,
        )
        for stop in BUS_STOPS
    )
    return subway_specs + bus_specs


def unique_id_for_sensor(key: str) -> str:
    """Return the stable Home Assistant unique ID for a sensor key."""

    return f"{DOMAIN}_{key}"


def native_minutes(arrival: Arrival | None, now: datetime | None = None) -> int | None:
    """Return a sensor native value from a normalized arrival."""

    if arrival is None:
        return None
    if arrival.estimated_arrival_at is not None:
        remaining = remaining_seconds_until_arrival(arrival, now)
        if remaining is None:
            return arrival.minutes
        return max(0, math.floor(remaining / 60))
    return arrival.minutes


def next_minute_change_delay(
    arrival: Arrival | None,
    now: datetime | None = None,
) -> float | None:
    """Return seconds until the displayed minute value should next change."""

    remaining = remaining_seconds_until_arrival(arrival, now)
    if remaining is None:
        return None

    current_minutes = math.floor(remaining / 60)
    if current_minutes <= 0:
        return None

    seconds_until_boundary = remaining - (current_minutes * 60)
    return max(
        COUNTDOWN_CHANGE_DELAY_SECONDS,
        seconds_until_boundary + COUNTDOWN_CHANGE_DELAY_SECONDS,
    )


def remaining_seconds_until_arrival(
    arrival: Arrival | None,
    now: datetime | None = None,
) -> float | None:
    """Return remaining seconds for arrivals with an estimated arrival time."""

    if arrival is None or arrival.estimated_arrival_at is None:
        return None
    if now is None:
        now = datetime.now(arrival.estimated_arrival_at.tzinfo)
    return max(0.0, (arrival.estimated_arrival_at - now).total_seconds())
