import os
import sys
import uuid
import json
import logging

import paho.mqtt.client as mqtt
from nut2 import PyNUTClient
from time import sleep


ENV_MQTT_PUB_ROOT = os.getenv("MQTT_PUB_ROOT", "UPS")
ENV_MQTT_CLIENTID = os.getenv(
    "MQTT_CLIENTID", "nut2mqtt/" + str(uuid.uuid4())
)
ENV_MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
ENV_MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
ENV_MQTT_USER = os.getenv("MQTT_USER", "")
ENV_MQTT_PASS = os.getenv("MQTT_PASS", "")
ENV_MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", 60))
ENV_NUT_HOST = os.getenv("NUT_HOST", "")
ENV_NUT_PORT = int(os.getenv("NUT_PORT", 3493))
ENV_NUT_USER = os.getenv("NUT_USER", "")
ENV_NUT_PASS = os.getenv("NUT_PASS", "")
ENV_NUT_INTR = int(os.getenv("NUT_INTR", 30))
ENV_DEBUG = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")


logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG if ENV_DEBUG else logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(filename)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt="%a, %d %b %Y %H:%M:%S",
)
logger = logging.getLogger("nut2mqtt")


# types allowed in KEYPAIRS below
CONFIG_TYPES = {"float": float, "int": int, "str": str, "bool": bool}
KEYPAIRS = {
    "battery.capacity": float,
    "battery.charge": int,
    "battery.charge.low": int,
    "battery.runtime": int,
    "input.frequency": float,
    "input.frequency.nominal": int,
    "input.voltage": float,
    "input.voltage.nominal": int,
    "output.current": float,
    "output.frequency": float,
    "output.frequency.nominal": int,
    "output.powerfactor": float,
    "output.voltage": float,
    "output.voltage.nominal": int,
    "ups.load": float,
    "ups.power": int,
    "ups.power.nominal": int,
    "ups.realpower": int,
    "ups.realpower.nominal": int,
    "ups.status": str,
}


def extract_datapoints(ups_name, ups_vars):
    tags = {"ups": ups_name}
    fields = {}

    for key, conv in KEYPAIRS.items():
        try:
            fields[key] = conv(ups_vars[key])
        except KeyError:
            logger.debug("UPS %s: var %s missing, skipping", ups_name, key)
        except (ValueError, TypeError) as e:
            logger.warning("UPS %s: bad value for %s: %s", ups_name, key, e)

    return [fields, tags]


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        logger.info("Connected to MQTT broker %s:%s", ENV_MQTT_HOST, ENV_MQTT_PORT)
    else:
        logger.warning("MQTT connect failed: %s", reason_code)


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties=None):
    if reason_code != 0:
        logger.warning("Unexpected MQTT disconnect: %s (will reconnect)", reason_code)


def create_mqtt_client():
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=ENV_MQTT_CLIENTID,
    )
    if ENV_MQTT_USER:
        client.username_pw_set(ENV_MQTT_USER, ENV_MQTT_PASS or None)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    return client


def mqtt_publish(client, data):
    payload = json.dumps(data)
    logger.debug("Publishing: %s", payload)
    info = client.publish(ENV_MQTT_PUB_ROOT, payload=payload, qos=1)
    if info.rc != mqtt.MQTT_ERR_SUCCESS:
        # while disconnected QoS1 messages are queued and flushed on reconnect;
        # rc != SUCCESS here means the message was dropped
        logger.warning("MQTT publish failed rc=%s", info.rc)
    return info.rc == mqtt.MQTT_ERR_SUCCESS


def connect_to_nut():
    try:
        nut = PyNUTClient(
            host=ENV_NUT_HOST,
            port=ENV_NUT_PORT,
            login=ENV_NUT_USER,
            password=ENV_NUT_PASS,
            debug=ENV_DEBUG,
        )
        nut.list_ups()  # verify the connection works before trusting it
    except Exception as e:
        logger.error("Can't connect to NUT host %s: %s", ENV_NUT_HOST, e)
        return None

    return nut


def main():
    mqtt_client = create_mqtt_client()
    mqtt_client.loop_start()
    mqtt_client.connect_async(ENV_MQTT_HOST, ENV_MQTT_PORT, keepalive=ENV_MQTT_KEEPALIVE)

    logger.info(
        "Started NUT exporter (interval=%ss, nut=%s:%s, mqtt=%s:%s)",
        ENV_NUT_INTR, ENV_NUT_HOST, ENV_NUT_PORT, ENV_MQTT_HOST, ENV_MQTT_PORT,
    )
    while True:
        nut = connect_to_nut()
        if nut is None:
            sleep(ENV_NUT_INTR)
            continue

        try:
            ups_list = nut.list_ups()
        except Exception as e:
            logger.error("Can't list UPS on %s: %s", ENV_NUT_HOST, e)
            sleep(ENV_NUT_INTR)
            continue

        for ups_name in ups_list:
            try:
                ups_vars = nut.list_vars(ups_name)
            except Exception as e:
                logger.error("UPS %s is having issues: %s", ups_name, e)
                continue

            data = extract_datapoints(ups_name, ups_vars)
            mqtt_publish(mqtt_client, data)

        sleep(ENV_NUT_INTR)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
