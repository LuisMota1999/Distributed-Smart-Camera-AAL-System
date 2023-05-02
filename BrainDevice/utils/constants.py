import random
import socket
from enum import Enum

class Network(Enum):
    HOST_NAME = socket.gethostname()
    SERVICE_TYPE = "_node._tcp.local."
    HOST_PORT = random.randint(5000, 6000)
    HOST_PORT_RECON = random.randint(7000, 8000)
    LEADER = "LEADER"
    FOLLOWER = "FOLLOWER"
    CANDIDATE = "CANDIDATE"
