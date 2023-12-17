import logging
import time
from EdgeDevice.NetworkService.Node import Node
from EdgeDevice.utils import HOST_NAME
from EdgeDevice.utils.helper import NetworkUtils


def main():
    NetworkUtils.generate_keys()
    NetworkUtils.generate_tls_keys()

    logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(message)s')
    time.sleep(2)
    node = Node(HOST_NAME)

    logging.info(f"Listening on {node.ip}:{node.port}...")

    node.start()


if __name__ == '__main__':
    main()
