"""Tests for Seoul Transit model helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from custom_components.seoul_transit.models import (
    COUNTDOWN_CHANGE_DELAY_SECONDS,
    Arrival,
    active_arrival_index,
    build_sensor_specs,
    clean_arrival_message,
    clean_station_name,
    native_minutes,
    next_minute_change_delay,
    public_arrival_attributes,
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
    ) == 1
    assert native_minutes(
        arrival,
        now=estimated_arrival_at - timedelta(seconds=60),
    ) == 1
    assert native_minutes(
        arrival,
        now=estimated_arrival_at - timedelta(seconds=59),
    ) == 0
    assert native_minutes(
        arrival,
        now=estimated_arrival_at + timedelta(seconds=1),
    ) == 0


def test_native_minutes_keeps_first_arrival_after_it_passes() -> None:
    now = datetime(2026, 6, 27, 18, 37, 38, tzinfo=SEOUL_TZ)
    second = Arrival(
        minutes=3,
        raw_message="3분 후",
        estimated_arrival_at=now + timedelta(seconds=190),
    )
    arrival = Arrival(
        minutes=1,
        raw_message="곧 도착",
        estimated_arrival_at=now + timedelta(seconds=10),
        following=(second,),
    )

    assert native_minutes(arrival, now=now) == 0
    assert active_arrival_index(arrival, now=now) == 1
    assert native_minutes(arrival, now=now + timedelta(seconds=11)) == 0
    assert active_arrival_index(arrival, now=now + timedelta(seconds=11)) == 1


def test_next_minute_change_delay_targets_display_boundaries() -> None:
    estimated_arrival_at = datetime(2026, 6, 27, 18, 37, 38, tzinfo=SEOUL_TZ)
    arrival = Arrival(
        minutes=3,
        raw_message="2분 31초 후",
        estimated_arrival_at=estimated_arrival_at,
    )

    assert next_minute_change_delay(
        arrival,
        now=estimated_arrival_at - timedelta(seconds=151),
    ) == 31 + COUNTDOWN_CHANGE_DELAY_SECONDS
    assert next_minute_change_delay(
        arrival,
        now=estimated_arrival_at - timedelta(seconds=120),
    ) == COUNTDOWN_CHANGE_DELAY_SECONDS
    assert (
        next_minute_change_delay(
            arrival,
            now=estimated_arrival_at - timedelta(seconds=59),
        )
        is None
    )


def test_next_minute_change_delay_tracks_second_arrival_without_rollover() -> None:
    now = datetime(2026, 6, 27, 18, 37, 38, tzinfo=SEOUL_TZ)
    second = Arrival(
        minutes=3,
        raw_message="3분 후",
        estimated_arrival_at=now + timedelta(seconds=190),
    )
    arrival = Arrival(
        minutes=1,
        raw_message="곧 도착",
        estimated_arrival_at=now + timedelta(seconds=10),
        following=(second,),
    )

    assert next_minute_change_delay(arrival, now=now) == (
        10 + COUNTDOWN_CHANGE_DELAY_SECONDS
    )


def test_native_minutes_uses_zero_for_position_only_arrival() -> None:
    arrival = Arrival(
        minutes=None,
        raw_message="[5]번째 전역 (청계산입구)",
        has_eta=False,
        attributes={"stops_away": 5},
    )

    assert native_minutes(arrival) == 0


def test_station_display_text_strips_parenthetical_suffixes() -> None:
    assert clean_station_name("어린이대공원(세종대)") == "어린이대공원"
    assert clean_station_name("군자(능동)") == "군자"
    assert (
        clean_arrival_message("13분 후 (숭실대입구(살피재))")
        == "13분 후 (숭실대입구)"
    )
    assert (
        clean_arrival_message("[5]번째 전역 (청계산입구)")
        == "[5]번째 전역 (청계산입구)"
    )


def test_public_arrival_attributes_use_same_shape_for_eta_and_position() -> None:
    received_at = datetime(2026, 6, 27, 18, 37, 38, tzinfo=SEOUL_TZ)
    eta_arrival = Arrival(
        minutes=3,
        raw_message="3분 후 (어린이대공원(세종대))",
        message="3분 후 (어린이대공원)",
        remaining_seconds=180,
        received_at=received_at,
        estimated_arrival_at=received_at + timedelta(seconds=180),
        destination="장암",
        current_location="어린이대공원",
        attributes={"arrival_code": "99"},
    )
    position_arrival = Arrival(
        minutes=None,
        raw_message="[5]번째 전역 (청계산입구)",
        message="[5]번째 전역 (청계산입구)",
        has_eta=False,
        current_location="청계산입구",
        attributes={
            "arrival_code": "99",
            "stops_away": 5,
            "position_station": "청계산입구",
            "position_type": "previous_station",
        },
    )

    eta_attrs = public_arrival_attributes(eta_arrival, now=received_at)
    position_attrs = public_arrival_attributes(position_arrival, now=received_at)

    assert eta_attrs.keys() == position_attrs.keys()
    assert eta_attrs["minutes"] == 3
    assert eta_attrs["has_eta"] is True
    assert position_attrs["minutes"] is None
    assert position_attrs["seconds"] is None
    assert position_attrs["has_eta"] is False
    assert position_attrs["stops_away"] == 5
