import paho.mqtt.client as mqtt
import json
import threading
from EdgeDevice.utils.constants import Homeassistant as HA


class Homeassistant(threading.Thread):
    def __init__(self):
        super().__init__()
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect

        if HA.MQTT_USERNAME and HA.MQTT_PASSWORD:
            self.client.username_pw_set(HA.MQTT_USERNAME.value, HA.MQTT_PASSWORD.value)

        try:
            self.client.connect(HA.MQTT_BROKER.value, HA.MQTT_PORT.value)
            self.client.loop_start()
        except Exception as e:
            print("Error connecting to MQTT broker:", e)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connection established with success!")
        else:
            print(f"Error Establishing connection: {rc}")

    def publish_message(self, message):
        try:
            result = self.client.publish(HA.MQTT_TOPIC.value, json.dumps(message, indent=2))
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print("Message published successfully")
            else:
                print(f"Error publishing message: {result.rc}")
        except Exception as e:
            print("Error publishing message:", e)
