import paho.mqtt.client as mqtt
import time
import cereal.messaging as messaging
import logging
import json
logging.basicConfig(level=logging.INFO)

TOPIC = "car/state"

sm = messaging.SubMaster(['carState'])
pm = messaging.PubMaster(['customReserved6'])


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
    else:
        print(f"Failed to connect, return code {rc}")
    client.subscribe(TOPIC)


def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    payload_size = len(msg.payload)
    data = json.loads(payload)
    print(f"Received message on {msg.topic}: {payload_size} bytes")
    rtt = time.time() - data['ts']
    print(f"RTT: {rtt*1000:.2f} ms")
    dat = messaging.new_message('customReserved6', valid=True)
    dat.customReserved6.msgSize = payload_size
    dat.customReserved6.rtt = rtt
    pm.send('customReserved6', dat)


def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect("192.168.1.230", 1883, 60)

    client.loop_start()
    try:
        while True:
            # sm.update(0)
            # if sm.updated['carState']:
            #     car_state = sm['carState']
            #     payload = {
            #         'ts': time.time(),
            #         'vEgo': car_state.vEgo,
            #         'angleSteers': car_state.angleSteers,
            #         'steeringPressed': car_state.steeringPressed
            #     }
            #     client.publish(TOPIC, json.dumps(payload))
            client.publish(TOPIC, json.dumps({
                'ts': time.time(),
                'vEgo': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
                'd1': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
                'd2': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
                'd3': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
            }))
            time.sleep(0.2) # 5 Hz
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()