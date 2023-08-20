import paho.mqtt.client as mqtt
import json

# Configurações do MQTT
MQTT_BROKER = "homeassistant"
MQTT_PORT = 1883
MQTT_USERNAME = "mqttc"  # Se o broker requer autenticação
MQTT_PASSWORD = "mqtt123"  # Se o broker requer autenticação
MQTT_TOPIC = "casa/mensagem"  # O mesmo tópico configurado no Home Assistant


# Função de callback para quando a conexão com o broker MQTT for estabelecida
def on_connect(client, userdata, flags, rc):
    print("Conectado com o código de resultado: " + str(rc))


# Cria um cliente MQTT
client = mqtt.Client()

# Define as funções de callback
client.on_connect = on_connect

# Se o broker MQTT requer autenticação, insira o nome do utilizador e a senha
if MQTT_USERNAME and MQTT_PASSWORD:
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# Conecta ao broker MQTT
client.connect(MQTT_BROKER, MQTT_PORT)

# Publica a mensagem no tópico configurado
mensagem = {
    "META": {
        "CLIENT": "0.0.1",
        "FROM_ADDRESS": {
            "UUID": "07b4ab99-504a-40d9-ad2a-69e4c47e21c8",
            "IP": "192.168.122.94",
            "PORT": 5929
        },
    },
    "PAYLOAD": {
        "TIME": 1689886629.4676633,
        "EVENT": "Watching_TV",
        "LOCAL": "SALA",
    }
}
client.publish(MQTT_TOPIC, json.dumps(mensagem, indent=2))

# Encerra a conexão com o broker MQTT
client.disconnect()
