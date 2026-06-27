"""API client and parsers for Seoul transit arrivals."""

from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

from .const import (
    BUS_STOPS,
    SUBWAY_LINE_NAMES,
    SUBWAY_STOPS,
    BusStop,
    SubwayStop,
)
from .models import (
    Arrival,
    clean_arrival_message,
    clean_station_name,
    subway_sensor_key,
)

SUBWAY_API_BASE = "http://swopenapi.seoul.go.kr/api/subway"
BUS_API_URL = "http://ws.bus.go.kr/api/rest/arrive/getArrInfoByRoute"

AUTH_MARKERS = ("KEY", "Key", "인증", "SERVICE KEY", "등록되지")
SEOUL_TZ = ZoneInfo("Asia/Seoul")
DATETIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y%m%d%H%M%S")
SUBWAY_POSITION_RE = re.compile(
    r"^\[(?P<stops>\d+)\]번째 전역 \((?P<station>.+)\)$"
)


class SeoulTransitError(Exception):
    """Base exception for Seoul Transit failures."""


class SeoulTransitAuthError(SeoulTransitError):
    """Raised when a remote API rejects an API key."""


class SeoulTransitConnectionError(SeoulTransitError):
    """Raised when a remote API cannot be reached or parsed."""


def _parse_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _seconds_to_minutes(seconds: int | None) -> int | None:
    if seconds is None:
        return None
    return max(0, math.ceil(seconds / 60))


def _minutes_from_message(message: str | None) -> int | None:
    if not message:
        return None
    if any(token in message for token in ("곧도착", "도착", "출발", "진입")):
        return 0
    match = re.search(r"(\d+)\s*분", message)
    if match:
        return int(match.group(1))
    return None


def _parse_local_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    for date_format in DATETIME_FORMATS:
        try:
            parsed = datetime.strptime(value.strip(), date_format)
            return parsed.replace(tzinfo=SEOUL_TZ)
        except ValueError:
            continue
    return None


def _estimated_arrival_at(
    received_at: datetime | None,
    remaining_seconds: int | None,
) -> datetime | None:
    if received_at is None or remaining_seconds is None:
        return None
    return received_at + timedelta(seconds=remaining_seconds)


def _subway_position_attributes(message: str | None) -> dict[str, Any]:
    if message is None:
        return {}
    match = SUBWAY_POSITION_RE.match(message.strip())
    if not match:
        return {}
    return {
        "stops_away": int(match.group("stops")),
        "position_station": clean_station_name(match.group("station")),
        "position_type": "previous_station",
    }


def _looks_like_auth_error(code: str | None, message: str | None) -> bool:
    combined = f"{code or ''} {message or ''}"
    return any(marker in combined for marker in AUTH_MARKERS)


def parse_subway_payload(
    payload: dict[str, Any],
    station_name: str | None = None,
    line_ids: set[str] | None = None,
) -> dict[tuple[str, str], list[Arrival]]:
    """Parse Seoul realtime subway JSON into arrivals by line and direction."""

    line_ids = line_ids or set(SUBWAY_LINE_NAMES)
    error = payload.get("errorMessage") or payload
    code = str(error.get("code") or "")
    message = str(error.get("message") or "")
    if code and code != "INFO-000":
        if _looks_like_auth_error(code, message):
            raise SeoulTransitAuthError(message or code)
        if code == "INFO-200":
            return {}
        raise SeoulTransitConnectionError(message or code)

    arrivals: dict[tuple[str, str], list[Arrival]] = {}
    for row in payload.get("realtimeArrivalList") or []:
        line_id = str(row.get("subwayId") or "")
        direction = str(row.get("updnLine") or "")
        if line_id not in line_ids or not direction:
            continue
        if station_name and row.get("statnNm") != station_name:
            continue

        raw_message = row.get("arvlMsg2")
        position_attributes = _subway_position_attributes(raw_message)
        seconds = _parse_int(row.get("barvlDt"))
        has_eta = not (seconds == 0 and position_attributes)
        eta_seconds = seconds if has_eta else None
        received_at = _parse_local_datetime(row.get("recptnDt"))
        arrival = Arrival(
            minutes=_seconds_to_minutes(eta_seconds),
            raw_message=raw_message,
            message=clean_arrival_message(raw_message),
            remaining_seconds=eta_seconds,
            received_at=received_at,
            estimated_arrival_at=_estimated_arrival_at(received_at, eta_seconds),
            has_eta=has_eta,
            destination=clean_station_name(row.get("bstatnNm")),
            current_location=clean_station_name(row.get("arvlMsg3")),
            generated_at=row.get("recptnDt"),
            vehicle_id=row.get("btrainNo"),
            line_id=line_id,
            line_name=SUBWAY_LINE_NAMES.get(line_id),
            direction=direction,
            station_name=clean_station_name(row.get("statnNm")),
            attributes={
                "train_line_name": row.get("trainLineNm"),
                "arrival_code": row.get("arvlCd"),
                "terminal_station_id": row.get("bstatnId"),
                "last_car": row.get("lstcarAt") == "1",
                **position_attributes,
            },
        )
        arrivals.setdefault((line_id, direction), []).append(arrival)

    for values in arrivals.values():
        values.sort(key=lambda item: (item.minutes is None, item.minutes or 0))
    return arrivals


def _find_text(root: ET.Element, name: str) -> str | None:
    node = root.find(f".//{name}")
    if node is None or node.text is None:
        return None
    return node.text.strip()


def parse_bus_payload(xml_text: str, stop: BusStop) -> Arrival | None:
    """Parse Seoul bus arrival XML for one route/stop pair."""

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as err:
        raise SeoulTransitConnectionError(f"Invalid bus XML: {err}") from err

    header_code = _find_text(root, "headerCd")
    header_message = _find_text(root, "headerMsg")
    if header_code and header_code != "0":
        if _looks_like_auth_error(header_code, header_message):
            raise SeoulTransitAuthError(header_message or header_code)
        if _find_text(root, "itemCount") == "0":
            return None
        raise SeoulTransitConnectionError(header_message or header_code)

    item = root.find(".//itemList")
    if item is None:
        return None

    def text(name: str) -> str | None:
        node = item.find(name)
        if node is None or node.text is None:
            return None
        value = node.text.strip()
        return value or None

    first_message = text("arrmsg1")
    first_seconds = _parse_int(text("traTime1"))
    first_minutes = _seconds_to_minutes(first_seconds)
    if first_minutes is None:
        first_minutes = _minutes_from_message(first_message)

    second_message = text("arrmsg2")
    second_seconds = _parse_int(text("traTime2"))
    second_minutes = _seconds_to_minutes(second_seconds)
    if second_minutes is None:
        second_minutes = _minutes_from_message(second_message)
    received_at = _parse_local_datetime(text("mkTm"))
    second_estimated_arrival_at = _estimated_arrival_at(received_at, second_seconds)

    return Arrival(
        minutes=first_minutes,
        raw_message=first_message,
        message=first_message,
        remaining_seconds=first_seconds,
        received_at=received_at,
        estimated_arrival_at=_estimated_arrival_at(received_at, first_seconds),
        has_eta=first_seconds is not None,
        destination=text("nxtStn"),
        current_location=text("sectNm"),
        generated_at=text("mkTm"),
        vehicle_id=text("plainNo1") or text("vehId1"),
        stop_name=text("stNm") or stop.name,
        stop_id=text("stId") or stop.stop_id,
        ars_id=text("arsId") or stop.ars_id,
        route_id=text("busRouteId") or stop.route_id,
        route_name=text("rtNm") or stop.route_name,
        attributes={
            "order": text("ord") or stop.order,
            "second_arrival_minutes": second_minutes,
            "second_arrival_message": second_message,
            "second_estimated_arrival_at": second_estimated_arrival_at,
            "second_vehicle_id": text("plainNo2") or text("vehId2"),
            "low_plate": text("busType1"),
            "reroute": text("isFullFlag1"),
        },
        following=(
            Arrival(
                minutes=second_minutes,
                raw_message=second_message,
                message=second_message,
                remaining_seconds=second_seconds,
                received_at=received_at,
                estimated_arrival_at=second_estimated_arrival_at,
                has_eta=second_seconds is not None,
                destination=text("nxtStn"),
                current_location=text("sectNm"),
                generated_at=text("mkTm"),
                vehicle_id=text("plainNo2") or text("vehId2"),
                stop_name=text("stNm") or stop.name,
                stop_id=text("stId") or stop.stop_id,
                ars_id=text("arsId") or stop.ars_id,
                route_id=text("busRouteId") or stop.route_id,
                route_name=text("rtNm") or stop.route_name,
            ),
        )
        if second_message
        else (),
    )


class SeoulTransitApiClient:
    """Small async client using Home Assistant's aiohttp session."""

    def __init__(
        self,
        session: Any,
        subway_api_key: str,
        bus_api_key: str | None = None,
    ) -> None:
        self._session = session
        self._subway_api_key = subway_api_key
        self._bus_api_key = bus_api_key

    async def async_fetch_subway(self) -> dict[str, list[Arrival]]:
        """Fetch and parse realtime arrivals for the configured subway stations."""

        results: dict[str, list[Arrival]] = {}
        for stop in SUBWAY_STOPS:
            arrivals = await self._async_fetch_subway_stop(stop)
            for (line_id, direction), values in arrivals.items():
                key = subway_sensor_key(line_id, direction, stop.key)
                results[key] = values
        return results

    async def _async_fetch_subway_stop(
        self,
        stop: SubwayStop,
    ) -> dict[tuple[str, str], list[Arrival]]:
        """Fetch and parse realtime arrivals for one configured subway station."""

        station = quote(stop.endpoint_name, safe="")
        url = (
            f"{SUBWAY_API_BASE}/{self._subway_api_key}/json/"
            f"realtimeStationArrival/0/40/{station}"
        )
        payload = await self._request_json(url)
        return parse_subway_payload(payload, stop.name, set(stop.line_ids))

    async def async_fetch_bus(self) -> dict[str, Arrival | None]:
        """Fetch and parse realtime arrivals for the configured bus stops."""

        results: dict[str, Arrival | None] = {}
        for stop in BUS_STOPS:
            params = {
                "serviceKey": self._bus_api_key,
                "stId": stop.stop_id,
                "busRouteId": stop.route_id,
                "ord": stop.order,
            }
            text = await self._request_text(BUS_API_URL, params=params)
            results[stop.key] = parse_bus_payload(text, stop)
        return results

    async def _request_json(self, url: str) -> dict[str, Any]:
        text = await self._request_text(url)
        try:
            return json.loads(text)
        except json.JSONDecodeError as err:
            raise SeoulTransitConnectionError(f"Invalid JSON response: {err}") from err

    async def _request_text(
        self, url: str, params: dict[str, str] | None = None
    ) -> str:
        try:
            async with self._session.get(url, params=params, timeout=15) as response:
                text = await response.text()
                if response.status in (401, 403):
                    raise SeoulTransitAuthError(f"HTTP {response.status}")
                if response.status >= 400:
                    raise SeoulTransitConnectionError(f"HTTP {response.status}")
                return text
        except SeoulTransitError:
            raise
        except TimeoutError as err:
            raise SeoulTransitConnectionError("Request timed out") from err
        except Exception as err:
            raise SeoulTransitConnectionError(str(err)) from err
