from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf, ServiceStateChange, ZeroconfServiceTypes, IPVersion
import Pyro4
import Pyro4.naming
import threading
import socket
import time
import argparse
import logging
from typing import cast
import random
import string

name = "node1"
service_type = "_node._tcp.local."
port = 5000


class NodeDiscovery(threading.Thread):
    def __init__(self):
        super().__init__()
        self.discovered_nodes = []
        self.zeroconf = Zeroconf()
        self.listener = NodeListener(self)
        self.running = True

    def run(self):
        # Start the service browser
        browser = ServiceBrowser(self.zeroconf, "_node._tcp.local.", [self.listener.update_service])

        # Start the socket server
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('localhost', 9000))
        server_socket.listen(5)

        while self.running:  # check running flag
            # Accept incoming connections from new devices
            client_socket, address = server_socket.accept()
            print(f"New device connected: {address[0]}")

            # Add the new device to the list of discovered nodes
            self.discovered_nodes.append(address[0])

            # Send keep-alive messages to all discovered nodes
            for ip in self.discovered_nodes:
                try:
                    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    conn.connect((ip, port))
                    conn.sendall(str(self.discovered_nodes).encode())
                    conn.close()
                except ConnectionRefusedError:
                    self.remove_node(ip)
                    continue

    def stop(self):
        self.running = False
        self.zeroconf.close()

    def add_node(self, ip):
        if ip not in self.discovered_nodes:
            self.discovered_nodes.append(ip)
            print(f"Node {ip} added to the network")
            print(f"Discovered nodes: {self.discovered_nodes}")

            # Send the list of discovered nodes to the newly added node

    def remove_node(self, ip):
        if ip in self.discovered_nodes:
            self.discovered_nodes.remove(ip)
            print(f"Node {ip} removed from the network")
            print(f"Discovered nodes: {self.discovered_nodes}")


class NodeListener:
    def __init__(self, node_discovery):
        self.node_discovery = node_discovery

    def remove_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if info:
            # uri = Pyro4.URI(f"PYRO:{info.server.lower()}:{info.port}")
            ip_address = info.properties[b'IP']
            ip_address = ip_address.decode('UTF-8')
            print(ip_address)
            self.node_discovery.remove_node(ip_address)

    def add_service(self, zeroconf, service_type, name):
        info = zeroconf.get_service_info(service_type, name)

        if info:
            ip_list = info.parsed_addresses()

            for ip in ip_list:

                self.node_discovery.add_node(ip)

                if ip != socket.gethostbyname(socket.gethostname()):
                    # Connect to the machine on the specified port
                    print("Connecting to", ip)
                    try:
                        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        conn.connect((ip, port))
                        conn.sendall(str(self.node_discovery.discovered_nodes).encode())
                        conn.close()
                    except ConnectionRefusedError:
                        self.node_discovery.remove_node(ip)
                        return
                    # conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    # conn.connect((ip, port))
                    # conn.send("Hello, world!".encode())
                    # data = conn.recv(1024)
                    # print("Received data:", data)
                    # conn.close()

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
        self.port = None
        self.discovered_nodes = []
        self.last_keep_alive = time.time()

    def get_discovered_nodes(self):
        return self.discovered_nodes

    def start(self):

        parser = argparse.ArgumentParser()

        # parser.add_argument("name", help="Node name")
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
        ip_address = socket.gethostbyname(hostname)

        service_info = ServiceInfo(
            type_="_node._tcp.local.",
            name=f"{self.name}._node._tcp.local.",
            addresses=[socket.inet_aton(ip_address)],
            port=port,
            weight=0,
            priority=0,
            properties={'IP': ip_address},
        )

        zc = Zeroconf(ip_version=ip_versionX)
        zc.register_service(service_info)


def main():
    node = Node(name)

    node_discovery = NodeDiscovery()
    node_discovery.start()
    time.sleep(2)
    node_thread = threading.Thread(target=node.start)
    node_thread.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        node_discovery.stop()


# pyro4-ns
if __name__ == "__main__":
    main()
