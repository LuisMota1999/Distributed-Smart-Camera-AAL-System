import paho.mqtt.client as mqtt

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

# Se o broker MQTT requer autenticação, insira o nome de usuário e senha
if MQTT_USERNAME and MQTT_PASSWORD:
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# Conecta ao broker MQTT
client.connect(MQTT_BROKER, MQTT_PORT)

# Publica a mensagem no tópico configurado
mensagem = "Olá, Home Assistant!"  # Sua mensagem
client.publish(MQTT_TOPIC, mensagem)

# Encerra a conexão com o broker MQTT
client.disconnect()
