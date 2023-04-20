import threading
import time
from zeroconf.browse import Node, NodeDiscovery
import socket

HOST_NAME = socket.gethostname()


def main():
    node = Node(HOST_NAME)
    print(f"Listening on {node.ip}:{node.port}...")
    node_discovery = NodeDiscovery(node.port)
    node_discovery.start()
    time.sleep(2)
    node_thread = threading.Thread(target=node.start)
    node_thread.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        node_discovery.stop()


if __name__ == "__main__":
    main()
