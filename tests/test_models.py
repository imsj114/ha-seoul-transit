"""Tests for Seoul Transit model helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from custom_components.seoul_transit.models import (
    Arrival,
    build_sensor_specs,
    native_minutes,
    subway_sensor_key,
    unique_id_for_sensor,
)

SEOUL_TZ = ZoneInfo("Asia/Seoul")


def test_build_sensor_specs_contains_v1_entities() -> None:
    specs = build_sensor_specs()

    assert len(specs) == 10
    assert {spec.key for spec in specs} == {
        "subway_line_5_up",
        "subway_line_5_down",
        "subway_line_7_up",
        "subway_line_7_down",
        "subway_nonhyeon_line_7_up",
        "subway_nonhyeon_line_7_down",
        "subway_nonhyeon_line_shinbundang_up",
        "subway_nonhyeon_line_shinbundang_down",
        "bus_2012_05241",
        "bus_2012_05242",
    }


def test_build_sensor_specs_can_exclude_bus_entities() -> None:
    specs = build_sensor_specs(include_bus=False)

    assert len(specs) == 8
    assert {spec.key for spec in specs} == {
        "subway_line_5_up",
        "subway_line_5_down",
        "subway_line_7_up",
        "subway_line_7_down",
        "subway_nonhyeon_line_7_up",
        "subway_nonhyeon_line_7_down",
        "subway_nonhyeon_line_shinbundang_up",
        "subway_nonhyeon_line_shinbundang_down",
    }
    assert {spec.source for spec in specs} == {"subway"}


def test_unique_ids_are_stable() -> None:
    assert unique_id_for_sensor("bus_2012_05241") == "seoul_transit_bus_2012_05241"
    assert subway_sensor_key("1005", "하행") == "subway_line_5_down"
    assert (
        subway_sensor_key("1077", "상행", "nonhyeon")
        == "subway_nonhyeon_line_shinbundang_up"
    )


def test_native_minutes_handles_unavailable_arrival() -> None:
    assert native_minutes(None) is None
    assert native_minutes(Arrival(minutes=3, raw_message="3분 후")) == 3


def test_native_minutes_counts_down_from_estimated_arrival_time() -> None:
    estimated_arrival_at = datetime(2026, 6, 27, 18, 37, 38, tzinfo=SEOUL_TZ)
    arrival = Arrival(
        minutes=2,
        raw_message="전역 도착",
        estimated_arrival_at=estimated_arrival_at,
    )

    assert native_minutes(
        arrival,
        now=estimated_arrival_at - timedelta(seconds=61),
    ) == 2
    assert native_minutes(
        arrival,
        now=estimated_arrival_at - timedelta(seconds=60),
    ) == 1
    assert native_minutes(
        arrival,
        now=estimated_arrival_at + timedelta(seconds=1),
    ) == 0
