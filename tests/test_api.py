"""Tests for Seoul Transit API parsers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.seoul_transit.api import (
    SeoulTransitAuthError,
    parse_bus_payload,
    parse_subway_payload,
)
from custom_components.seoul_transit.const import BUS_STOPS

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_subway_payload_filters_gunja_lines_and_sorts() -> None:
    payload = json.loads((FIXTURES / "subway_gunja.json").read_text())

    arrivals = parse_subway_payload(payload)

    assert set(arrivals) == {
        ("1005", "상행"),
        ("1005", "하행"),
        ("1007", "상행"),
        ("1007", "하행"),
    }
    first_line_5_up = arrivals[("1005", "상행")][0]
    assert first_line_5_up.minutes == 2
    assert first_line_5_up.line_name == "5호선"
    assert first_line_5_up.station_name == "군자(능동)"
    assert first_line_5_up.destination == "방화"
    assert arrivals[("1005", "상행")][1].minutes == 8


def test_parse_subway_payload_no_data_is_empty() -> None:
    payload = {"status": 500, "code": "INFO-200", "message": "해당하는 데이터가 없습니다."}

    assert parse_subway_payload(payload) == {}


def test_parse_bus_payload_success() -> None:
    xml_text = (FIXTURES / "bus_success.xml").read_text()

    arrival = parse_bus_payload(xml_text, BUS_STOPS[0])

    assert arrival is not None
    assert arrival.minutes == 4
    assert arrival.raw_message == "3분 20초후[2번째 전]"
    assert arrival.stop_id == "104000148"
    assert arrival.ars_id == "05241"
    assert arrival.route_name == "2012"
    assert arrival.attributes["second_arrival_minutes"] == 10
    assert arrival.vehicle_id == "서울70사1234"


def test_parse_bus_payload_no_arrival() -> None:
    xml_text = (FIXTURES / "bus_no_arrival.xml").read_text()

    assert parse_bus_payload(xml_text, BUS_STOPS[0]) is None


def test_parse_bus_payload_auth_failure_does_not_leak_key() -> None:
    xml_text = (FIXTURES / "bus_auth_failure.xml").read_text()

    with pytest.raises(SeoulTransitAuthError) as exc_info:
        parse_bus_payload(xml_text, BUS_STOPS[0])

    assert "SERVICE KEY" in str(exc_info.value)
    assert "d2a911" not in str(exc_info.value)

