"""Constants for the Seoul Transit integration."""

from __future__ import annotations

from dataclasses import dataclass

DOMAIN = "seoul_transit"

CONF_SUBWAY_API_KEY = "subway_api_key"
CONF_BUS_API_KEY = "bus_api_key"
CONF_SUBWAY_SCAN_INTERVAL = "subway_scan_interval"
CONF_BUS_SCAN_INTERVAL = "bus_scan_interval"

OLD_DEFAULT_SUBWAY_SCAN_INTERVAL = 120
V2_DEFAULT_SUBWAY_SCAN_INTERVAL = 90
DEFAULT_SUBWAY_SCAN_INTERVAL = 180
DEFAULT_BUS_SCAN_INTERVAL = 180
MIN_SCAN_INTERVAL = 30
LOCAL_COUNTDOWN_UPDATE_INTERVAL = 30

PLATFORMS = ["sensor"]


@dataclass(frozen=True)
class SubwayStop:
    """A fixed Seoul subway station used by this integration."""

    key: str
    name: str
    label: str
    endpoint_name: str
    line_ids: tuple[str, ...]


SUBWAY_LINE_NAMES: dict[str, str] = {
    "1005": "5호선",
    "1007": "7호선",
    "1077": "신분당선",
}

SUBWAY_LINE_KEYS: dict[str, str] = {
    "1005": "5",
    "1007": "7",
    "1077": "shinbundang",
}

SUBWAY_DIRECTIONS: tuple[str, str] = ("상행", "하행")

SUBWAY_STOPS: tuple[SubwayStop, ...] = (
    SubwayStop(
        key="gunja",
        name="군자(능동)",
        label="군자",
        endpoint_name="군자(능동)",
        line_ids=("1005", "1007"),
    ),
    SubwayStop(
        key="nonhyeon",
        name="논현",
        label="논현",
        endpoint_name="논현",
        line_ids=("1007", "1077"),
    ),
)

BUS_ROUTE_ID = "100100186"
BUS_ROUTE_NAME = "2012"


@dataclass(frozen=True)
class BusStop:
    """A fixed Seoul bus route stop used by this integration."""

    key: str
    stop_id: str
    ars_id: str
    order: str
    name: str
    route_id: str = BUS_ROUTE_ID
    route_name: str = BUS_ROUTE_NAME


BUS_STOPS: tuple[BusStop, ...] = (
    BusStop(
        key="bus_2012_05241",
        stop_id="104000148",
        ars_id="05241",
        order="38",
        name="군자동주민센터",
    ),
    BusStop(
        key="bus_2012_05242",
        stop_id="104000149",
        ars_id="05242",
        order="77",
        name="군자동주민센터",
    ),
)
