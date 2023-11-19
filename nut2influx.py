#!/usr/bin/env python3
# 

import json
import socket
import os
import collections.abc
import sys
import logging
import traceback

from pprint import pprint
from nut2 import PyNUTClient
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime
from time import sleep
from typing import Tuple, Mapping, Iterable

debug = False


DEFAULT_CONFIG = {
    "nut": {
        "interval": 30,
        "host": "localhost",
        "port": 3493,
        "creds": None,
        "vars": {}
    },
    "influx": {
        "host": "https://localhost:8086",
        "token": None,
        "org": "myorg",
        "bucket": "mybucket",
        "influx_tags": {
            "ups": "E5130_A"
        }
    }
}

# types allowed in nut_vars in the config
CONFIG_TYPES = {
    'float': float,
    'int': int,
    'str': str,
    'bool': bool
}


class RequestError(Exception):
    pass


def _recursive_update(d: Mapping, u: Mapping):
    """
    Recursively update a dictionary
    Parameters:
    d -- dictionary to update
    u -- updated mapping
    """
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            r = _recursive_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def extractDatapoints(ups_name, UPS_var, varsToExtract: Mapping[str, type],):
    tags = {"ups": ups_name}
    fields = {}

    for var, info in varsToExtract.items():
        try:
            fields[info['measurement_name']] = info['type'](UPS_var[var])
        except RequestError as e:
            logging.debug('RequestError: {}, skipping!'.format(
                e.args), file=sys.stderr)
            continue

    result = {
        'measurement': 'ups',
        'tags': tags,
        'fields': fields
    }

    return result


def uploadToInflux(config, data):  # Main upload

    client = InfluxDBClient(
        url=config['influx']['url'], token=config['influx']['token'], org=config['influx']['org'], debug=True)
    
    if client and debug:
        logging.debug("influx: online")
        for _, logger in client.conf.loggers.items():
            logger.setLevel(logging.DEBUG)
            logger.addHandler(logging.StreamHandler(sys.stdout))

    write_api = client.write_api(write_options=SYNCHRONOUS)

    for UPS in data:
        dp = extractDatapoints(UPS, data[UPS], config['nut']['vars'])

        logging.debug(
            "INFLUX: " + config['influx']['bucket'] + " @ " + config['influx']['url'])
        logging.debug(json.dumps(dp, indent=4))
        try:
            write_api.write(bucket=config['influx']['bucket'],
                            org=config['influx']['org'], record=[dp])
        except:
            tb = traceback.format_exc()
    client.close()

def LoadConfig(file):
    new_config = DEFAULT_CONFIG.copy()
    if file is None:
        user_config = {}
    else:
        with open(file) as f:
            user_config = json.load(f)
    _recursive_update(new_config, user_config)
    # convert the strings in nut_vars to real types to simplify conversion
    for _, var in new_config['nut']['vars'].items():
        var['type'] = CONFIG_TYPES[var['type']]
    return new_config


def ConnectToNut(config):
    nutcfg = config['nut']
    username = nutcfg['creds'][0] if nutcfg['creds'] is not None else None
    password = nutcfg['creds'][1] if nutcfg['creds'] is not None else None
    port = nutcfg['port'] if nutcfg['port'] is not None else None
    try:
        nut = PyNUTClient(nutcfg['host'], port=port,
                          login=username, password=password, debug=debug)
    except:
        logging.debug("Can't connect to %s" % nutcfg['host'])
        return None

    return nut


if __name__ == '__main__':
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', help='config file')
    p.add_argument('--debug', help='Debugging')
    args = p.parse_args()
    config = LoadConfig(args.config)

    interval = config['nut']["interval"]
    logging.basicConfig(stream = sys.stdout, level=logging.WARNING,
                        format="[%(levelname)s] %(message)s")
    if args.debug:
        debug=True
        # Print DEBUG messages to the console.
        logging.basicConfig(level=logging.WARNING,
                        format="[%(levelname)s] %(message)s")
        logging.getLogger().setLevel(logging.DEBUG)

    logging.info("Started NUT exporter")
    while True:
        nut = ConnectToNut(config)
        if nut:
            list_ups = {}
            upslist = {}
            data = {}

            logging.debug("Fetching list of UPS")
            try:
                list_ups = nut.list_ups()
            except:
                logging.debug("Can't connect to %s" % config['nut']['host'])
                nut = None

            logging.debug("Fetching list of UPS variables")
            for UPS in list_ups.keys():
                try:
                    data[UPS] = nut.list_vars(UPS)
                except:
                    logging.debug('UPS {} is having issues'.format(host))

            uploadToInflux(config, data)

        else:
            logging.debug("Can't connect to UPS host")

        sleep(interval)
