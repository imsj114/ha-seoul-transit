"""Constants for the Seoul Transit integration."""

from __future__ import annotations

from dataclasses import dataclass

DOMAIN = "seoul_transit"

CONF_SUBWAY_API_KEY = "subway_api_key"
CONF_BUS_API_KEY = "bus_api_key"
CONF_SUBWAY_SCAN_INTERVAL = "subway_scan_interval"
CONF_BUS_SCAN_INTERVAL = "bus_scan_interval"

DEFAULT_SUBWAY_SCAN_INTERVAL = 120
DEFAULT_BUS_SCAN_INTERVAL = 180
MIN_SCAN_INTERVAL = 30

PLATFORMS = ["sensor"]

SUBWAY_STATION_NAME = "군자(능동)"
SUBWAY_ENDPOINT_STATION_NAME = "군자(능동)"

SUBWAY_LINES: dict[str, str] = {
    "1005": "5호선",
    "1007": "7호선",
}

SUBWAY_DIRECTIONS: tuple[str, str] = ("상행", "하행")

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

