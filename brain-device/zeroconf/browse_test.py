from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf, ServiceStateChange, ZeroconfServiceTypes, IPVersion
import threading
import socket
import time
import argparse
import logging
from typing import cast
import netifaces as ni
import random

HOST_NAME = socket.gethostname()
SERVICE_TYPE = "_node._tcp.local."
HOST_PORT = random.randint(5000, 6000)


class NodeDiscovery(threading.Thread):
    def __init__(self,port):
        super().__init__()
        self.discovered_nodes = set()
        self.zeroconf = Zeroconf()
        self.port = port
        self.listener = NodeListener(self)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', port))  # ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
        self.socket.listen(10)
        self.running = True

    def run(self):
        # Start the service browser
        browser = ServiceBrowser(self.zeroconf, "_node._tcp.local.", [self.listener.update_service])
        threading.Thread(target=self.accept_connections).start()

    def accept_connections(self):
        while self.running:
            conn, addr = self.socket.accept()
            print(f"Connected to {addr[0]}:{addr[1]}")

            # Start a thread to handle incoming messages
            threading.Thread(target=self.handle_messages, args=(conn,)).start()

    def connect_to_peer(self, host, port):
        i = 1
        while True:
            try:
                conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                conn.connect((host, port))
                # print(f"Connected to {host}:{port}")

                while i <= 10:
                    message = input(f"Enter a message to {host}:{port}:")
                    self.send_message(f"\n[Message]: {message}")
                    i += 1

                break
            except ConnectionRefusedError:
                print(f"Connection refused by {host}:{port}, retrying in 10 seconds...")
                time.sleep(10)

        # Start a thread to handle incoming messages
        threading.Thread(target=self.handle_messages, args=(conn,)).start()

    def send_message(self, message):
        for peer in self.discovered_nodes:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect(peer)
            conn.sendall(message.encode())

    def handle_messages(self, conn):
        while True:
            message = conn.recv(1024).decode()
            if not message:
                break
            print(f"Received message: {message}")

    def list_peers(self):
        print("Connected peers:")
        for peer in self.discovered_nodes:
            print(peer)

    def stop(self):
        self.running = False
        self.zeroconf.close()

    def add_node(self, client_ip, client_port):
        if client_ip not in self.discovered_nodes:
            self.discovered_nodes.add((client_ip, client_port))
            print(f"Node {client_ip} added to the network")
            print(f"Discovered nodes: {self.discovered_nodes}")

    def remove_node(self, ip):
        if ip in self.discovered_nodes:
            self.discovered_nodes.remove(ip)
            print(f"Node {ip} removed from the network")
            print(f"Nodes still available: {self.discovered_nodes}")


class NodeListener:
    def __init__(self, node_discovery):
        self.node_discovery = node_discovery

    def remove_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if info:
            ip_address = info.properties[b'IP']
            ip_address = ip_address.decode('UTF-8')
            self.node_discovery.remove_node(ip_address)

    def add_service(self, zeroconf, service_type, name):
        info = zeroconf.get_service_info(service_type, name)
        if info:
            ip_list = info.parsed_addresses()
            print(f"IP LIST: {ip_list}")
            for ip in ip_list:
                self.node_discovery.add_node(ip, info.port)
                if ip != ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']:
                    self.node_discovery.connect_to_peer(ip, info.port)

    def update_service(self,
                       zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange
                       ) -> None:
        print(f"Service {name} of type {service_type} state changed: {state_change}")

        if state_change is ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            # print("Info from zeroconf.get_service_info: %r" % (info))

            if info:
                addresses = ["%s:%d" % (addr, cast(int, info.port)) for addr in info.parsed_scoped_addresses()]
                print("  Addresses: %s" % ", ".join(addresses))
                print("  Weight: %d, priority: %d" % (info.weight, info.priority))
                print(f"  Server: {info.server}")
                if info.properties:
                    print("  Properties are:")
                    for key, value in info.properties.items():
                        print(f"    {key}: {value}")
                else:
                    print("  No properties")

                self.add_service(zeroconf, service_type, name)
            else:
                print("  No info")
            print('\n')


class Node:
    def __init__(self, name):
        self.name = name
        self.ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
        self.port = HOST_PORT
        self.discovered_nodes = []
        self.last_keep_alive = time.time()

    def get_discovered_nodes(self):
        return self.discovered_nodes

    def start(self):

        parser = argparse.ArgumentParser()
        parser.add_argument('--debug', action='store_true')
        parser.add_argument('--find', action='store_true', help='Browse all available services')
        version_group = parser.add_mutually_exclusive_group()
        version_group.add_argument('--v6', action='store_true')
        version_group.add_argument('--v6-only', action='store_true')
        args = parser.parse_args()

        if args.debug:
            logging.getLogger('zeroconf').setLevel(logging.DEBUG)
        if args.v6:
            ip_versionX = IPVersion.All
        elif args.v6_only:
            ip_versionX = IPVersion.V6Only
        else:
            ip_versionX = IPVersion.V4Only

        hostname = socket.gethostname()

        print(f"HOSTNAME - {hostname}")
        service_info = ServiceInfo(
            type_="_node._tcp.local.",
            name=f"{self.name}._node._tcp.local.",
            addresses=[socket.inet_aton(self.ip)],
            port=HOST_PORT,
            weight=0,
            priority=0,
            properties={'IP': self.ip},
        )

        zc = Zeroconf(ip_version=ip_versionX)
        zc.register_service(service_info)


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
