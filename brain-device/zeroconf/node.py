from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf, ServiceStateChange, ZeroconfServiceTypes, IPVersion
import threading
import socket
import time
import argparse
import logging
from typing import cast
import netifaces as ni

name = socket.gethostname()
service_type = "_node._tcp.local."
port = 12345


class NodeDiscovery(threading.Thread):
    def __init__(self):
        super().__init__()
        self.discovered_nodes = []
        self.zeroconf = Zeroconf()
        self.listener = NodeListener(self)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', port)) #ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
        self.socket.listen(10)

        self.running = True

    def run(self):
        # Start the service browser
        browser = ServiceBrowser(self.zeroconf, "_node._tcp.local.", [self.listener.update_service])

        while self.running:  # check running flag
            # Accept incoming connections from new devices

            try:
                conn, addr = self.socket.accept()
                print(addr, conn)
                print(f"New connection from {addr[0]}")
                # conn.send(str(f"HELLO WORLD  {name}!").encode())

            except ConnectionRefusedError:
                continue

    def stop(self):
        self.running = False
        self.zeroconf.close()

    def add_node(self, ip):
        if ip not in self.discovered_nodes:
            self.discovered_nodes.append(ip)
            print(f"Node {ip} added to the network")
            print(f"Discovered nodes: {self.discovered_nodes}")

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
            ip_address = info.properties[b'IP']
            ip_address = ip_address.decode('UTF-8')
            self.node_discovery.remove_node(ip_address)

    def add_service(self, zeroconf, service_type, name):
        info = zeroconf.get_service_info(service_type, name)

        if info:
            ip_list = info.parsed_addresses()

            for ip in ip_list:
                self.node_discovery.add_node(ip)
                # print(f"{ip}, {ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']}")
                if ip != ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']:
                    try:
                        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        conn.connect((ip, port))
                        message = "Teste abc"
                        conn.send(message.encode())
                        data = conn.recv(1024)
                        print("Received data:", data)
                    except ConnectionRefusedError:
                        print("Connection Refused Error")
                        # return

    def update_service(self,
                       zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange
                       ) -> None:
        print(f"Service {name} of type {service_type} state changed: {state_change}")

        if state_change is ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)

            if info:
                self.add_service(zeroconf, service_type, name)
            else:
                print("No info")
            print('\n')


class Node:
    def __init__(self, name):
        self.name = name
        self.ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
        self.port = None
        self.peers = []
        self.last_keep_alive = time.time()
        self.ip_version = IPVersion.V4Only
        self.serviceInfo = ServiceInfo(
            type_="_node._tcp.local.",
            name=f"{self.name}._node._tcp.local.",
            addresses=[socket.inet_aton(self.ip)],
            port=port,
            weight=0,
            priority=0,
            properties={'IP': self.ip},
        )
        zc = Zeroconf(ip_version=self.ip_version)
        zc.register_service(self.service_info)
        
    def get_discovered_nodes(self):
        return self.peers

    def handle_incoming_connections(self,server_socket):
        while True:
            # Accept incoming connections from new devices
            conn, addr = server_socket.accept()
            print(f"New connection from {addr[0]}")

            # Add the new node to the list of discovered nodes
            self.add_node(addr[0])

            # Start a thread to handle messages from the new node
            threading.Thread(target=self.handle_messages, args=(conn,), daemon=True).start()
    
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
        
        # Create a socket and listen for incoming connections
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('0.0.0.0', port))
        server_socket.listen()

        threading.Thread(target=self.handle_incoming_connections, args=(server_socket,), daemon=True).start()


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
