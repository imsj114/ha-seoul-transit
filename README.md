# Seoul Transit for Home Assistant

Home Assistant custom integration for selected Seoul transit arrivals:

- Subway: Gunja / 군자(능동), Seoul subway lines 5 and 7
- Subway: Nonhyeon / 논현, Seoul subway line 7 and Shinbundang line
- Bus: Seoul bus 2012 at both Gunja-dong Community Service Center stops
  when a bus API key is configured

This repository intentionally does not contain API keys.

## Sensors

The integration always creates eight subway duration sensors whose state is
minutes until the next arrival:

- `군자 5호선 상행`
- `군자 5호선 하행`
- `군자 7호선 상행`
- `군자 7호선 하행`
- `논현 7호선 상행`
- `논현 7호선 하행`
- `논현 신분당선 상행`
- `논현 신분당선 하행`

If a bus API key is entered, it also creates two bus sensors:

- `2012 군자동주민센터 05241`
- `2012 군자동주민센터 05242`

Each API refresh stores an estimated arrival timestamp from the API receipt time
plus the API-provided remaining seconds. Sensor states use conservative floored
minutes for the first train only, clamp at `0`, and schedule local updates for
minute boundaries between API refreshes. The state does not roll over to the
second train when the first train has passed, but the second train is exposed as
structured attributes and can keep counting down locally. Subway API refreshes
default to every 180 seconds, which keeps the two station endpoint calls under
roughly 1,000 calls per day.

Attributes include cleaned display station names, raw and cleaned arrival
messages, API-provided remaining time, estimated arrival timestamp, destination,
current location, generated timestamp, vehicle ID, and `first_arrival` /
`second_arrival` dictionaries with the same shape. When the subway API provides
position-only data such as `[2]번째 전역 (강남)`, the arrival has `has_eta: false`,
`minutes: null`, `stops_away: 2`, and `position_station: 강남` so dashboards can
display `2번째 전역` instead of treating it as an exact `0분` ETA.

## API Keys

Use separate keys for the two providers. The subway key is required; the bus key
is optional and can be left blank for subway-only setup.

- Subway: Seoul Open Data Plaza realtime subway key from
  <https://data.seoul.go.kr/together/mypage/actkeyMain.do>
- Bus: Public Data Portal bus arrival API application from
  <https://www.data.go.kr/data/15000314/openapi.do>

Enter the keys only through the Home Assistant config flow. Do not commit keys to
this repository.

If the bus API returns `SERVICE KEY IS NOT REGISTERED`, the key is not active for
the Seoul bus arrival API yet. Confirm that the Public Data Portal application is
approved for service `15000314`, then retry after the portal has propagated the
key.

## HACS Installation

This repository is meant to be installed as a HACS custom repository:

1. In Home Assistant, open HACS.
2. Open custom repositories.
3. Add this GitHub repository URL as an `Integration`.
4. Install `Seoul Transit`.
5. Restart Home Assistant.
6. Add the `Seoul Transit` integration from Settings > Devices & services.

## Dashboard Example

After the entities are created, adjust the entity IDs to match Home Assistant's
generated IDs:

```yaml
type: entities
title: Transit
entities:
  - entity: sensor.gunja_5_line_up
    name: 5호선 상행
  - entity: sensor.gunja_5_line_down
    name: 5호선 하행
  - entity: sensor.gunja_7_line_up
    name: 7호선 상행
  - entity: sensor.gunja_7_line_down
    name: 7호선 하행
  - entity: sensor.nonhyeon_7_line_up
    name: 논현 7호선 상행
  - entity: sensor.nonhyeon_7_line_down
    name: 논현 7호선 하행
  - entity: sensor.nonhyeon_shinbundang_line_up
    name: 논현 신분당선 상행
  - entity: sensor.nonhyeon_shinbundang_line_down
    name: 논현 신분당선 하행
```

Optional bus entities, when a bus key is configured:

```yaml
type: entities
title: Bus
entities:
  - entity: sensor.bus_2012_05241
    name: 2012 05241
  - entity: sensor.bus_2012_05242
    name: 2012 05242
```

## Development

Run local parser tests:

```bash
python -m compileall custom_components tests
pytest
```

The test suite uses static fixtures only. Live smoke tests should pass API keys
through environment variables or the Home Assistant config flow, never through
tracked files.
