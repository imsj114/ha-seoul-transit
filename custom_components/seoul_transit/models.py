"""Pure data models shared by the Seoul Transit integration and tests."""

from __future__ import annotations

import math
import re
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
STATION_SUFFIX_RE = re.compile(r"\s*\([^)]*\)\s*$")


@dataclass(frozen=True)
class Arrival:
    """A normalized transit arrival."""

    minutes: int | None
    raw_message: str | None
    message: str | None = None
    remaining_seconds: int | None = None
    received_at: datetime | None = None
    estimated_arrival_at: datetime | None = None
    has_eta: bool = True
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
    following: tuple[Arrival, ...] = field(default_factory=tuple)


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
    remaining = remaining_seconds_until_arrival(arrival, now)
    if remaining is not None:
        return max(0, math.floor(remaining / 60))
    if arrival.minutes is not None:
        return arrival.minutes
    return 0 if arrival.raw_message is not None else None


def next_minute_change_delay(
    arrival: Arrival | None,
    now: datetime | None = None,
) -> float | None:
    """Return seconds until the displayed minute value should next change."""

    delays: list[float] = []
    for candidate in ordered_arrivals(arrival):
        remaining = remaining_seconds_until_arrival(candidate, now)
        if remaining is None:
            continue

        current_minutes = math.floor(remaining / 60)
        if current_minutes <= 0:
            continue

        seconds_until_boundary = remaining - (current_minutes * 60)
        delays.append(
            max(
                COUNTDOWN_CHANGE_DELAY_SECONDS,
                seconds_until_boundary + COUNTDOWN_CHANGE_DELAY_SECONDS,
            )
        )

    if not delays:
        return None
    return min(delays)


def active_arrival_index(
    arrival: Arrival | None,
    now: datetime | None = None,
) -> int | None:
    """Return the arrival number currently used for the sensor state."""

    return 1 if arrival is not None else None


def active_estimated_arrival_at(
    arrival: Arrival | None,
    now: datetime | None = None,
) -> datetime | None:
    """Return the estimated arrival time currently used for the sensor state."""

    return arrival.estimated_arrival_at if arrival else None


def active_arrival_remaining_seconds(
    arrival: Arrival | None,
    now: datetime | None = None,
) -> tuple[int, float] | None:
    """Return the active arrival number and remaining seconds for display."""

    remaining = remaining_seconds_until_arrival(arrival, now)
    if remaining is None:
        return None
    return (1, remaining)


def ordered_arrivals(arrival: Arrival | None) -> tuple[Arrival, ...]:
    """Return the primary arrival followed by any later arrivals."""

    if arrival is None:
        return ()
    return (arrival, *arrival.following)


def remaining_seconds_until_arrival(
    arrival: Arrival | None,
    now: datetime | None = None,
) -> float | None:
    """Return remaining seconds for arrivals with an estimated arrival time."""

    if arrival is None or arrival.estimated_arrival_at is None:
        return None
    return _remaining_seconds_until(arrival.estimated_arrival_at, now)


def _remaining_seconds_until(
    estimated_arrival_at: datetime,
    now: datetime | None = None,
) -> float | None:
    """Return signed remaining seconds for one estimated arrival time."""

    if now is None:
        now = datetime.now(estimated_arrival_at.tzinfo)
    return (estimated_arrival_at - now).total_seconds()


def _second_estimate(arrival: Arrival | None) -> datetime | None:
    if arrival is None:
        return None
    if arrival.following:
        return arrival.following[0].estimated_arrival_at
    value = arrival.attributes.get("second_estimated_arrival_at")
    return value if isinstance(value, datetime) else None


def clean_station_name(value: str | None) -> str | None:
    """Return a display station name without parenthetical suffixes."""

    if value is None:
        return None
    return STATION_SUFFIX_RE.sub("", value).strip() or None


def clean_arrival_message(value: str | None) -> str | None:
    """Return an arrival message with parenthetical station suffixes stripped."""

    if value is None:
        return None
    message = value.strip()
    marker = " ("
    if not message.endswith(")") or marker not in message:
        return message or None
    prefix, station = message.rsplit(marker, 1)
    return f"{prefix} ({clean_station_name(station[:-1])})"


def public_arrival_attributes(
    arrival: Arrival,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return one arrival in the public structured attribute shape."""

    seconds = arrival.remaining_seconds
    minutes = arrival.minutes
    remaining = remaining_seconds_until_arrival(arrival, now)
    if remaining is not None:
        seconds = max(0, math.floor(remaining))
        minutes = max(0, math.floor(remaining / 60))

    return {
        "message": arrival.message,
        "raw_message": arrival.raw_message,
        "minutes": minutes,
        "seconds": seconds,
        "estimated_arrival_at": _isoformat(arrival.estimated_arrival_at),
        "has_eta": arrival.has_eta,
        "destination": clean_station_name(arrival.destination),
        "current_location": clean_station_name(arrival.current_location),
        "generated_at": arrival.generated_at,
        "received_at": _isoformat(arrival.received_at),
        "vehicle_id": arrival.vehicle_id,
        "train_line_name": arrival.attributes.get("train_line_name"),
        "arrival_code": arrival.attributes.get("arrival_code"),
        "terminal_station_id": arrival.attributes.get("terminal_station_id"),
        "last_car": arrival.attributes.get("last_car"),
        "stops_away": arrival.attributes.get("stops_away"),
        "position_station": arrival.attributes.get("position_station"),
        "position_type": arrival.attributes.get("position_type"),
    }


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
