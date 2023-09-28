import random
import socket
from enum import Enum

HOST_PORT = random.randint(5000, 6000)
BUFFER_SIZE = 4096


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
    MESSAGE_TYPE_REQUEST_TRANSACTION = "REQUEST_TRANSACTION"
    MESSAGE_TYPE_RESPONSE_TRANSACTION = "RECEIVE_TRANSACTION"
    MESSAGE_TYPE_REQUEST_CHAIN = "REQUEST_CHAIN"
    MESSAGE_TYPE_RESPONSE_CHAIN = "RESPONSE_CHAIN"
    MESSAGE_TYPE_REQUEST_BLOCK = "BLOCK"
    MESSAGE_TYPE_RESPONSE_BLOCK = "BLOCK"


class Transaction(Enum):
    TYPE_AUDIO_INFERENCE = "AUDIO INFERENCE"
    TYPE_VIDEO_INFERENCE = "VIDEO INFERENCE"
    TYPE_NETWORK = "NETWORK"


class Homeassistant(Enum):
    MQTT_BROKER = "192.168.0.237"
    MQTT_PORT = 1883
    MQTT_USERNAME = "mqttc"
    MQTT_PASSWORD = "mqtt123"
    MQTT_TOPIC = "casa/mensagem"


class Inference(Enum):
    VIDEO_LABEL = 'models/movinet_retrained_class.txt'
    VIDEO_MODEL = 'models/movinet_a0_int8.tflite'
    VIDEO_NUM_THREADS = 4
    VIDEO_MAX_RESULTS = 4
    VIDEO_ALLOW_LIST = ['watching tv', 'washing dishes', 'reading book', 'eating burger', 'opening door']
    VIDEO_DENY_LIST = ['playing pinball', 'auctioning']
