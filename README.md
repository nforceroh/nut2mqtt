# nut2mqtt

Publishes UPS telemetry from a [NUT](https://networkupstools.org/) server to
MQTT as a single JSON payload per poll.

Built on `python:3.12-alpine` — the `nut2` client library still imports
`telnetlib`, which was removed from the standard library in Python 3.13.

## Usage

```yaml
services:
  nut2mqtt:
    image: ghcr.io/nforceroh/nut2mqtt:latest
    env_file: .env
    restart: unless-stopped
```

Copy `.env.example` to `.env` and fill it in. `.env` is gitignored.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `MQTT_PUB_ROOT` | `UPS` | Topic the JSON payload is published to |
| `MQTT_HOST` | `localhost` | MQTT broker host |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `MQTT_USER` | *(empty)* | MQTT username; anonymous when unset |
| `MQTT_PASS` | *(empty)* | MQTT password |
| `MQTT_KEEPALIVE` | `60` | MQTT keepalive, seconds |
| `NUT_HOST` | *(empty)* | NUT server host |
| `NUT_PORT` | `3493` | NUT server port |
| `NUT_USER` | *(empty)* | NUT username |
| `NUT_PASS` | *(empty)* | NUT password |
| `NUT_INTR` | `30` | Poll interval, seconds |
| `DEBUG` | `False` | Verbose logging |

## Payload

One message per UPS per poll, published to `MQTT_PUB_ROOT`:

```json
[
  {"battery.charge": 100, "ups.status": "OL", "ups.load": 12.0},
  {"ups": "E5130_A"}
]
```

The first element holds the fields, the second the tags. Only the keys listed
in `KEYPAIRS` in `content/app/nut2mqtt/main.py` are published; missing or
unparseable values are skipped and logged.

## Local development

```sh
make build   # build the image
make test    # build, then run tests/run_tests.sh
make run     # run with .env
```

CI is the only publisher — see
[nforceroh/.github](https://github.com/nforceroh/.github) for the shared
build and cleanup workflows.

## NUT server configs

`nut/` holds the NUT server-side configuration (`ups.conf`, `upsd.conf`,
`upsmon.conf`, ...) for the host running the NUT daemon. It is reference
material and is not copied into the image.
