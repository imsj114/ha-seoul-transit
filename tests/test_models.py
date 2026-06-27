"""Tests for Seoul Transit model helpers."""

from __future__ import annotations

from custom_components.seoul_transit.models import (
    Arrival,
    build_sensor_specs,
    native_minutes,
    subway_sensor_key,
    unique_id_for_sensor,
)


def test_build_sensor_specs_contains_v1_entities() -> None:
    specs = build_sensor_specs()

    assert len(specs) == 6
    assert {spec.key for spec in specs} == {
        "subway_line_5_up",
        "subway_line_5_down",
        "subway_line_7_up",
        "subway_line_7_down",
        "bus_2012_05241",
        "bus_2012_05242",
    }


def test_unique_ids_are_stable() -> None:
    assert unique_id_for_sensor("bus_2012_05241") == "seoul_transit_bus_2012_05241"
    assert subway_sensor_key("1005", "하행") == "subway_line_5_down"


def test_native_minutes_handles_unavailable_arrival() -> None:
    assert native_minutes(None) is None
    assert native_minutes(Arrival(minutes=3, raw_message="3분 후")) == 3

