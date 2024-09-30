import os
import time

import paho.mqtt.client as mqtt
from dotenv import load_dotenv, find_dotenv

import cereal.messaging as messaging
import cereal
from openpilot.common.params import Params
import json


LEAD_COMMA_DONGLE_ID = "abcd1234zzzz"
MQTT_CONFIG = {
    'host': 'chimpanzee.rmq.cloudamqp.com',
    'port': 1883,
}

pm = None
my_dongle_id = 'bdda168c0c35fad7'

def main():
    print("Dongle ID: ", my_dongle_id)
    print(os.getenv('MQTT_USERNAME'))

    mqtt_client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        my_dongle_id,
    )
    mqtt_client.username_pw_set(os.getenv('MQTT_USERNAME'), os.getenv('MQTT_PASSWORD'))

    mqtt_client.on_connect = handle_mqtt_on_connect
    mqtt_client.on_message = handle_mqtt_on_message

    mqtt_client.connect(MQTT_CONFIG['host'], MQTT_CONFIG['port'])

    mqtt_client.loop_forever()

def handle_mqtt_on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print("Connected to MQTT broker successfully")
        # Subscribe to a topic once connected
        client.subscribe(f"{LEAD_COMMA_DONGLE_ID}")
    else:
        print(f"Failed to connect with code {rc}")

def handle_mqtt_on_message(client, userdata, msg):
    # just publish the same message back
    client.publish(f"{my_dongle_id}", msg.payload)
    print(f"Received message: {msg.info}")

if __name__ == "__main__":
    # Load env from base directory
    load_dotenv()
    main()
