import os
import time
import logging
import sys
import uuid
import json

import paho.mqtt.client as mqtt
from pprint import pprint
from nut2 import PyNUTClient
from datetime import datetime
from time import sleep
from typing import Tuple, Mapping, Iterable


ENV_MQTT_PUB_ROOT = os.getenv("MQTT_PUB_ROOT", "UPS")
ENV_MQTT_CLIENTID = os.getenv(
    "MQTT_CLIENTID", f"paho-mqtt-python/issue72/" + str(uuid.uuid4())
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
ENV_DEBUG = os.getenv("DEBUG", False) == "True"


logger = logging.getLogger("")
if ENV_DEBUG:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

sh = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    "[%(asctime)s] %(levelname)s [%(filename)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt="%a, %d %b %Y %H:%M:%S",
)
sh.setFormatter(formatter)
logger.addHandler(sh)


class RequestError(Exception):
    pass


def extractDatapoints(ups_name="Unknown", UPS_var=None):
    # types allowed in nut_vars in the config
    CONFIG_TYPES = {"float": float, "int": int, "str": str, "bool": bool}
    keypairs = {
        "battery.capacity": {"type": "float"},
        "battery.charge": {"type": "int"},
        "battery.charge.low": {"type": "int"},
        "battery.runtime": {"type": "int"},
        "input.frequency": {"type": "float"},
        "input.frequency.nominal": {"type": "int"},
        "input.voltage": {"type": "float"},
        "input.voltage.nominal": {"type": "int"},
        "output.current": {"type": "float"},
        "output.frequency": {"type": "float"},
        "output.frequency.nominal": {"type": "int"},
        "output.powerfactor": {"type": "float"},
        "output.voltage": {"type": "float"},
        "output.voltage.nominal": {"type": "int"},
        "ups.load": {"type": "float"},
        "ups.power": {"type": "int"},
        "ups.power.nominal": {"type": "int"},
        "ups.realpower": {"type": "int"},
        "ups.realpower.nominal": {"type": "int"},
        "ups.status": {"type": "str"},
    }

    tags = {"ups": ups_name}
    fields = {}

    for key, value in keypairs.items():
        try:
            fields[key] = CONFIG_TYPES[value["type"]](UPS_var[key])
        except RequestError as e:
            logging.debug("RequestError: {}, skipping!".format(e.args), file=sys.stderr)
            continue

    result = [fields, tags]

    return result


def mqtt_publish(data):
    logger.debug("Write points: {0}".format(data))
    client = mqtt.Client(
        client_id=ENV_MQTT_CLIENTID,
        clean_session=None,
        userdata=None,
        transport="tcp",
        reconnect_on_failure=True,
    )  # create new instance
    logging.info(f"Dumping: %s" % json.dumps(data))
    client.connect(host=ENV_MQTT_HOST, port=int(ENV_MQTT_PORT))  # connect to broker
    client.publish(ENV_MQTT_PUB_ROOT, payload=json.dumps(data))  # publish


def ConnectToNut():
    D=False
    if ENV_DEBUG:
        D=True
    try:
        nut = PyNUTClient(
            host=ENV_NUT_HOST,
            port=ENV_NUT_PORT,
            login=ENV_NUT_USER,
            password=ENV_NUT_PASS,
            debug=D,
        )

    except:
        logging.debug("Can't connect to %s" % ENV_NUT_HOST)
        return None

    return nut


if __name__ == "__main__":
    scaninterval = ENV_NUT_INTR
    logging.basicConfig(
        stream=sys.stdout, level=logging.WARNING, format="[%(levelname)s] %(message)s"
    )
    logging.info("Started NUT exporter")
    while True:
        nut = ConnectToNut()
        if nut:
            list_ups = {}
            upslist = {}
            data = {}

            logging.debug("Fetching list of UPS")
            try:
                list_ups = nut.list_ups()
            except:
                logging.debug("Can't connect to UPS host")
                nut = None
            if list_ups:
                logging.debug("Fetching list of UPS variables")
                for UPS in list_ups.keys():
                    try:
                        data = nut.list_vars(UPS)
                    except:
                        logging.debug("UPS {} is having issues")

                    if data:
                        dp = extractDatapoints(UPS, data)
                        mqtt_publish(dp)

        else:
            logging.debug("Can't connect to UPS host")

        sleep(scaninterval)
