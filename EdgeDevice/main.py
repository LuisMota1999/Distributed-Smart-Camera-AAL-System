from EdgeDevice.NetworkService.Node import Node
from EdgeDevice.utils import HOST_NAME
from EdgeDevice.utils.helper import generate_keys


def main():
    generate_keys()
    node = Node(HOST_NAME)
    print(f"Listening on {node.ip}:{node.port}...")
    node.start()


if __name__ == '__main__':
    main()
