import paho.mqtt.client as mqtt
import json
import threading
from EdgeDevice.utils.constants import Homeassistant as HA


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        client.subscribe("home/temperature")
    else:
        print("Failed to connect to MQTT broker")


def on_message(client, userdata, msg):
    print(f"Received message on topic {msg.topic}: {msg.payload.decode()}")


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
if HA.MQTT_USERNAME and HA.MQTT_PASSWORD:
    client.username_pw_set(HA.MQTT_USERNAME.value, HA.MQTT_PASSWORD.value)
# Set the IP address or hostname of your Home Assistant system
broker_address = "192.168.0.237"

client.connect(broker_address, 1883, 60)
message = {"data": "test2"}
client.publish(HA.MQTT_TOPIC.value, json.dumps(message, indent=2))
client.loop_forever()
