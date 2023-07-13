import argparse
import logging

from EdgeDevice.NetworkService.Node import Node
from EdgeDevice.utils import HOST_NAME
from EdgeDevice.utils.helper import generate_keys, generate_tls_keys


def main():
    generate_keys()
    generate_tls_keys()

    logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(message)s')

    node = Node(HOST_NAME)

    logging.info(f"Listening on {node.ip}:{node.port}...")

    node.start()


if __name__ == '__main__':
    main()
