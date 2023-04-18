from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf, ServiceStateChange, ZeroconfServiceTypes, IPVersion
import threading
import socket
import time
import argparse
import logging
from typing import cast
import netifaces as ni
import random
name = socket.gethostname()
service_type = "_node._tcp.local."
port = random.randint(5000,6000)
num_connections = 5

class NodeDiscovery(threading.Thread):
    def __init__(self):
        super().__init__()
        self.discovered_nodes = []
        self.zeroconf = Zeroconf()
        self.listener = NodeListener(self)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((ni.ifaddresses('eth0')[ni.AF_INET][0]['addr'], port)) #
        self.socket.listen(num_connections)

        self.running = True

    def run(self):
        # Start the service browser
        browser = ServiceBrowser(self.zeroconf, "_node._tcp.local.", [self.listener.update_service])

        while self.running:  # check running flag
            # Accept incoming connections from new devices

            try:
                
                clientSocket, clientAddr = self.socket.accept()
                print(clientAddr, clientSocket)
                print(f"New connection from {clientAddr[0]}")
                #message = input("Enter a new message to send:")
                clientSocket.sendall(str(f"Welcome to the network {clientAddr[0]}").encode())
                client_thread = threading.Thread(target=self.handle_client, args=(clientSocket, clientAddr))
                client_thread.start()
                #trigger_message = clientSocket.recv(1024)
                #print(f'{name} received a trigger message from {clientAddr[0]}:', trigger_message.decode())
                
            except ConnectionRefusedError:
                continue

    def handle_client(clientSocket,clientAddress):
        # Receive data from the client
        data = clientSocket.recv(1024)
        print(f'Received data from {clientAddress}: {data}')

        # Send data back to the client
        clientSocket.send(b'Received your message!')

        # Close the client connection
        clientSocket.close()

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

            for ip in ip_list:
                self.node_discovery.add_node(ip)
                # print(f"{ip}, {ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']}")
                if ip != ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']:
                    try:
                        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        conn.connect((ip, port))
                        message = f'Reply {name}!'
                        conn.sendall(message.encode())
                        msg = conn.recv(1024)
                        print(f"Received data from machine {ip}:", msg.decode('utf-8'))
                        
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
                addresses = ["%s:%d" % (addr, cast(int, info.port)) for addr in info.parsed_scoped_addresses()]
                print("  Addresses: %s" % ", ".join(addresses))
                print("  Weight: %d, priority: %d" % (info.weight, info.priority))
                print(f"  Server: {info.server}")
                self.add_service(zeroconf, service_type, name)
            else:
                print("  No info")
            print('\n')


class Node:
    def __init__(self, name):
        self.name = name
        self.ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
        self.port = None
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

        service_info = ServiceInfo(
            type_="_node._tcp.local.",
            name=f"{self.name}._node._tcp.local.",
            addresses=[socket.inet_aton(self.ip)],
            port=port,
            weight=0,
            priority=0,
            properties={'IP': self.ip},
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

#https://gist.github.com/victorazzam/b34e9fb3d4b1e84e9c1841635071201d
