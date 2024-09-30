import os
import time

import paho.mqtt.client as mqtt
from dotenv import load_dotenv, find_dotenv

import cereal.messaging as messaging
import cereal
from openpilot.common.params import Params
import json


LEAD_COMMA_DONGLE_ID = "bdda168c0c35fad7"
MQTT_CONFIG = {
    'host': 'chimpanzee.rmq.cloudamqp.com',
    'port': 1883,
}

pm = None

def main():
    global pm
    dongle_byte = Params().get("DongleId")
    if dongle_byte is None:
        my_dongle_id = 'abcd1234zzzz'
        print("Dongle ID not found, using default: ", my_dongle_id)
    else:
        my_dongle_id = dongle_byte.decode('utf-8')
    print("Dongle ID: ", my_dongle_id)
    print(os.getenv('MQTT_USERNAME'))

    sm = messaging.SubMaster(['carState', 'carControl', 'modelV2'],poll='modelV2')
    pm = messaging.PubMaster(['customReserved2'])

    mqtt_client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        my_dongle_id,
    )
    mqtt_client.username_pw_set(os.getenv('MQTT_USERNAME'), os.getenv('MQTT_PASSWORD'))

    mqtt_client.on_connect = handle_mqtt_on_connect
    mqtt_client.on_message = handle_mqtt_on_message

    mqtt_client.connect(MQTT_CONFIG['host'], MQTT_CONFIG['port'])


    while True:
        sm.update()
        update_mqtt(sm, mqtt_client, my_dongle_id)
        mqtt_client.loop()


def update_mqtt(sm, client, dongle_id):
    CS = sm['carState']
    dat = messaging.new_message('customReserved2')
    dat.customReserved2.vCruise = CS.vCruise
    dat.customReserved2.aEgo = CS.aEgo
    dat.customReserved2.vEgo = CS.vEgo
    dat.customReserved2.lastEpochNs = time.time_ns()
    dat.valid = CS.canValid
    data_bytes = dat.to_bytes()
    client.publish(f"{dongle_id}", data_bytes)


def handle_mqtt_on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print("Connected to MQTT broker successfully")
        # Subscribe to a topic once connected
        client.subscribe(f"{LEAD_COMMA_DONGLE_ID}")
    else:
        print(f"Failed to connect with code {rc}")

def handle_mqtt_on_message(client, userdata, msg):
    global pm
    dat = messaging.log_from_bytes(msg.payload)
    print(dat.to_dict())
    pm.send('customReserved2', msg.payload)

if __name__ == "__main__":
    # Load env from base directory
    load_dotenv()
    main()
