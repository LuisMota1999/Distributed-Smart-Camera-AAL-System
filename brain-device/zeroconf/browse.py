import time
from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf, ServiceStateChange, ZeroconfServiceTypes, IPVersion, \
    NonUniqueNameException
import threading
import socket
import argparse
import logging
from typing import cast
import netifaces as ni
import random
from ..blockchain.blockchain import Blockchain

HOST_NAME = socket.gethostname()
SERVICE_TYPE = "_node._tcp.local."
HOST_PORT = random.randint(5000, 6000)
HOST_PORT_RECON = random.randint(7000, 8000)


class NodeListener:
    def __init__(self, node):
        self.node = node

    def add_service(self, zeroconf, service_type, name):
        info = zeroconf.get_service_info(service_type, name)
        if info:
            ip_list = info.parsed_addresses()
            for ip in ip_list:
                if ip != self.node.ip:  # and ip not in self.node.connections.getpeername()[0]:
                    self.node.connect_to_peer(ip, info.port)

    def update_service(self,
                       zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange
                       ) -> None:
        print(f"Service {name} of type {service_type} state changed: {state_change}")

        if state_change is ServiceStateChange.Added or ServiceStateChange.Updated:
            info = zeroconf.get_service_info(service_type, name)
            if info:
                addresses = ["%s:%d" % (addr, cast(int, info.port)) for addr in info.parsed_addresses()]
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



class Node(threading.Thread):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
        self.port = HOST_PORT
        self.last_keep_alive = time.time()
        self.keep_alive_timeout = 10
        self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
        self.listener = NodeListener(self)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', self.port))
        self.socket.listen(5)
        self.running = True
        self.connections = []
        self.blockchain = Blockchain()
        self.recon_state = False
        self.service_info = ServiceInfo(
            type_="_node._tcp.local.",
            name=f"{self.name}._node._tcp.local.",
            addresses=[socket.inet_aton(self.ip)],
            port=HOST_PORT,
            weight=0,
            priority=0,
            properties={'IP': self.ip},
        )

        self.blockchain.register_node({self.ip: time.time()})

    def starter(self):

        parser = argparse.ArgumentParser()
        parser.add_argument('--debug', action='store_true')
        parser.add_argument('--find', action='store_true', help='Browse all available services')
        version_group = parser.add_mutually_exclusive_group()
        version_group.add_argument('--v6', action='store_true')
        version_group.add_argument('--v6-only', action='store_true')
        args = parser.parse_args()

        if args.debug:
            logging.getLogger('zeroconf').setLevel(logging.DEBUG)

        hostname = socket.gethostname()
        print(f"HOSTNAME - {hostname}")
        try:
            self.zeroconf.register_service(self.service_info)
        except NonUniqueNameException as ex:
            self.zeroconf.update_service(self.service_info)

        # threading.Thread(target=self.handle_reconnects).start()
        threading.Thread(target=self.handle_reconnects).start()

    def run(self):
        try:
            # Start the service browser
            print("Searching new nodes on local network..")
            browser = ServiceBrowser(self.zeroconf, "_node._tcp.local.", [self.listener.update_service])
            threading.Thread(target=self.accept_connections).start()
        except KeyboardInterrupt:
            pass
            # self.broadcast_message("Shutting down")
            # self.stop()

    def accept_connections(self):

        while self.running:
            conn, addr = self.socket.accept()
            print(f"Connected to {addr[0]}:{addr[1]}")

            # Start a thread to handle incoming messages
            threading.Thread(target=self.handle_messages, args=(conn,)).start()

    def validate(self, ip, port):
        flag = True
        for connection in self.connections:
            if ip != connection.getpeername()[0] and port != connection.getpeername()[1]:
                flag = True
            else:
                flag = False
        return flag

    def handle_reconnects(self):
        while True:
            if len(self.connections) < 1 and self.recon_state is True:
                self.blockchain.nodes[self.ip] = time.time()
                print("Attempting to reconnect...")
                time.sleep(self.keep_alive_timeout)
            elif len(self.connections) > 0 and self.recon_state is True:
                self.recon_state = False
                self.broadcast_message("BC")
                time.sleep(2)
                continue

    def connect_to_peer(self, client_host, client_port):
        if self.validate(client_host,client_port) is not True or self.ip == client_host:
            print(f"Already connected to {client_host, client_port}")
            return

        while self.running:
            try:
                conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                conn.connect((client_host, client_port))
                conn.settimeout(20.0)

                self.add_node(conn)
                self.list_peers()
                #self.recon_state = False
                break

            except ConnectionRefusedError:
                print(f"Connection refused by {client_host}:{client_port}, retrying in 10 seconds...")
                time.sleep(10)
        try:

            handle_messages = threading.Thread(target=self.handle_messages, args=(conn,))
            handle_messages.start()

            send_keep_alive_msg = threading.Thread(target=self.send_keep_alive_messages, args=(conn,))
            send_keep_alive_msg.start()

            # handle_reconnects = threading.Thread(target=self.handle_reconnects)
            # handle_reconnects.start()
        except:
            print(f'Machine {conn.getpeername()[0]} is shutted down')

    def send_keep_alive_messages(self, conn):
        while self.running:
            try:
                # send keep alive message
                conn.send(b"ping")
                time.sleep(self.keep_alive_timeout)
            except:
                break

        # close connection and remove node from list
        if conn in self.connections:
            self.remove_node(conn, "KAlive")
            conn.close()

    def handle_messages(self, conn):
        while self.running:
            try:
                message = conn.recv(1024).decode()
                if message == "ping":
                    conn.send(b"pong")
                if not message:
                    self.service_info.priority = random.randint(1, 100)
                    self.zeroconf.update_service(self.service_info)
                    break
                if message == "BC":
                    print("BC")
            except socket.timeout:
                print("Timeout")
                self.recon_state = True
                if conn in self.connections:
                    self.remove_node(conn, "Timeout")
                    conn.close()
                break

            except OSError as e:
                print(f"System Error {e.strerror}")
                if conn in self.connections:
                    self.remove_node(conn, "OSError")
                    conn.close()
                break

            except Exception as ex:
                print(f"Exception Error {ex.args}")
                if conn in self.connections:
                    self.remove_node(conn, "Exception")
                    conn.close()
                break

            except ConnectionResetError as c:
                print(f"Connection Reset Error {c.strerror}")
                if conn in self.connections:
                    self.remove_node(conn, "ConnectionResetError")
                    conn.close()
                break

    def broadcast_message(self, message):
        for peer in self.connections:
            peer.sendall(message.encode())

    def list_peers(self):
        print("\n\nPeers:")
        for i, conn in enumerate(self.connections):
            print(f"[{i}] <{conn.getpeername()[0]}:{conn.getpeername()[1]}>")
        print("\n\n")

    def stop(self):
        self.running = False
        self.zeroconf.close()

    def add_node(self, conn):
        for connections in self.connections:
            if connections.getpeername()[0] == conn.getpeername()[0]:
                return

        if conn not in self.connections:
            self.connections.append(conn)
            self.blockchain.register_node({conn.getpeername()[0]: time.time()})
            print(f"Node {conn.getpeername()[0]} added to the network")
            print(f"Nodes in Blockchain: [IP:TIMESTAMP]{self.blockchain.nodes}")

    def remove_node(self, conn, function):
        print(f"Removed by {function}")
        if conn in self.connections:
            print(f"Node {conn} removed from the network")
            self.connections.remove(conn)
        print(f"Nodes still available:")
        self.list_peers()

