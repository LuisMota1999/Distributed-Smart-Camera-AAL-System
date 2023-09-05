import paho.mqtt.client as mqtt
import json
import threading
from EdgeDevice.utils.constants import Homeassistant as HA
import logging


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
            logging.error(f"Error connecting to MQTT broker: {e}")

    @staticmethod
    def on_connect(rc):
        if rc == 0:
            logging.info(f"Connection established with success {rc}")
        else:
            logging.error(f"Error Establishing connection {rc}")

    def publish_message(self, message):
        try:
            result = self.client.publish(HA.MQTT_TOPIC.value, json.dumps(message, indent=2))
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logging.info("Message published successfully")
            else:
                logging.error(f"Error publishing message: {result.rc}")
        except Exception as e:
            logging.error("Error publishing message:", e)
