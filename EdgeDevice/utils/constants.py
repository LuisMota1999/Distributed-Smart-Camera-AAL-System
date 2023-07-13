import random
import socket
from enum import Enum

HOST_PORT = random.randint(5000, 6000)


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
    MESSAGE_TYPE_TRANSACTION = "TRANSACTION"
    MESSAGE_TYPE_GET_CHAIN = "GET_CHAIN"
    MESSAGE_TYPE_CHAIN_RESPONSE = "CHAIN_RESPONSE"
    MESSAGE_TYPE_BLOCK = "BLOCK"


class Config(Enum):
    BUFFER_SIZE = 8192
