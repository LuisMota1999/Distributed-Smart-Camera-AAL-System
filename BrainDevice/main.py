import threading
import time
from BrainDevice.NetworkBootstrap.browse import Node
import socket

HOST_NAME = socket.gethostname()


def main():
    node = Node(HOST_NAME)
    print(f"Listening on {node.ip}:{node.port}...")
    node.start()
    time.sleep(2)
    node_thread = threading.Thread(target=node.starter)
    node_thread.start()


if __name__ == "__main__":
    main()

