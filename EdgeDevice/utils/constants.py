import random
import socket
from enum import Enum

HOST_PORT = random.randint(5000, 6000)
BUFFER_SIZE = 1024


class Network(Enum):
    HOST_NAME = socket.gethostname()
    SERVICE_TYPE = "_node._tcp.local."
    HOST_PORT_RECON = random.randint(7000, 8000)
    COORDINATOR = "COORDINATOR"
    FOLLOWER = "FOLLOWER"
    CANDIDATE = "CANDIDATE"


class Messages(Enum):
    # Define constants for message types
    MESSAGE_TYPE_PING = "PING"
    MESSAGE_TYPE_PONG = "PONG"
    MESSAGE_TYPE_SEND_TRANSACTION = "SEND_TRANSACTION"
    MESSAGE_TYPE_RECEIVE_TRANSACTION = "RECEIVE_TRANSACTION"
    MESSAGE_TYPE_GET_CHAIN = "GET_CHAIN"
    MESSAGE_TYPE_CHAIN_RESPONSE = "CHAIN_RESPONSE"
    MESSAGE_TYPE_BLOCK = "BLOCK"


class Transaction(Enum):
    TYPE_INFERENCE = "INFERENCE"
    TYPE_NETWORK = "NETWORK"


class Homeassistant(Enum):
    MQTT_BROKER = "homeassistant"
    MQTT_PORT = 1883
    MQTT_USERNAME = "mqttc"
    MQTT_PASSWORD = "mqtt123"
    MQTT_TOPIC = "casa/mensagem"
