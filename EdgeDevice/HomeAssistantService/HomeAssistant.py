import paho.mqtt.client as mqtt
import json
import time

from EdgeDevice.utils.constants import Homeassistant as HA
from EdgeDevice.utils.helper import MessageHandlerUtils


class Homeassistant(object):
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect

        if HA.MQTT_USERNAME and HA.MQTT_PASSWORD:
            self.client.username_pw_set(HA.MQTT_USERNAME.value, HA.MQTT_PASSWORD.value)

        try:
            self.client.connect(HA.MQTT_BROKER.value, HA.MQTT_PORT.value)
            self.client.loop_start()

            time.sleep(2)

            if not self.client.is_connected():
                print("MQTT Connection was denied")
            else:
                print("MQTT Connection is active")

                # Publica a mensagem no tópico configurado
                mensagem = MessageHandlerUtils.create_homeassistant_message("07b4ab99-504a-40d9-ad2a-69e4c47e21c8",
                                                                            "192.168.122.94", 5929, "Watching_TV",
                                                                            "SALA")
                try:
                    self.client.publish(HA.MQTT_TOPIC.value, json.dumps(mensagem, indent=2))
                    print("Message published successfully")
                except mqtt.MQTT_LOG_ERR as e:
                    print("Error publishing message:", e)

        except Exception as e:
            print("Error:", e)

        finally:
            self.client.loop_stop()
            self.client.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connection established with success!")
        else:
            print(f"Error Establishing connection: {rc}")

