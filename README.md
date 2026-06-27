# Seoul Transit for Home Assistant

Home Assistant custom integration for the next arrivals near Gunja:

- Subway: Gunja / 군자(능동), Seoul subway lines 5 and 7
- Bus: Seoul bus 2012 at both Gunja-dong Community Service Center stops
  when a bus API key is configured

This repository intentionally does not contain API keys.

## Sensors

The v1 integration always creates four subway duration sensors whose state is
minutes until the next arrival:

- `군자 5호선 상행`
- `군자 5호선 하행`
- `군자 7호선 상행`
- `군자 7호선 하행`

If a bus API key is entered, it also creates two bus sensors:

- `2012 군자동주민센터 05241`
- `2012 군자동주민센터 05242`

Each API refresh stores an estimated arrival timestamp from the API receipt time
plus the API-provided remaining seconds. Sensor states count down locally every
30 seconds between API refreshes, so the dashboard stays fresh without increasing
API traffic. Subway API refreshes default to every 90 seconds.

Attributes include raw arrival message, API-provided remaining time, estimated
arrival timestamp, destination, current location, generated timestamp, vehicle
ID, and second-arrival data when the API provides it.

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
