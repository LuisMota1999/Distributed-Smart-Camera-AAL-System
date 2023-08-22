import paho.mqtt.client as mqtt
import json
import time

from EdgeDevice.utils.constants import Homeassistant
from EdgeDevice.utils.helper import MessageHandlerUtils


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connection established with success!")
    else:
        print(f"Error Establishing connection: {rc}")


client = mqtt.Client()

client.on_connect = on_connect

if Homeassistant.MQTT_USERNAME and Homeassistant.MQTT_PASSWORD:
    client.username_pw_set(Homeassistant.MQTT_USERNAME.value, Homeassistant.MQTT_PASSWORD.value)

try:
    client.connect(Homeassistant.MQTT_BROKER.value, Homeassistant.MQTT_PORT.value)
    client.loop_start()

    time.sleep(2)

    if not client.is_connected():
        print("MQTT Connection was denied")
    else:
        print("MQTT Connection is active")

        # Publica a mensagem no tópico configurado
        mensagem = MessageHandlerUtils.create_homeassistant_message("07b4ab99-504a-40d9-ad2a-69e4c47e21c8",
                                                                    "192.168.122.94", 5929, "Watching_TV", "SALA")
        try:
            client.publish(Homeassistant.MQTT_TOPIC.value, json.dumps(mensagem, indent=2))
            print("Message published successfully")
        except mqtt.MQTT_LOG_ERR as e:
            print("Error publishing message:", e)

except Exception as e:
    print("Error:", e)

finally:
    client.loop_stop()
    client.disconnect()
