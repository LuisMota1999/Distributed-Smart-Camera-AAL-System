import time
from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf, ServiceStateChange, IPVersion, \
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
        """
        Initializes a new instance of the NodeListener class.

        :param node: An instance of the Node class representing the local node that will use this listener.
        """
        self.node = node

    def add_service(self, zeroconf, service_type, name):
        """
        Adds a service to the node's peer list, if it is not already present.

        This method retrieves the IP addresses of the service and adds them as peers, if they are different from
        the IP address of the node itself. It uses the Zeroconf instance to get the service information.

        :param zeroconf: The Zeroconf instance that discovered the service.
        :type zeroconf: Zeroconf
        :param service_type: The type of the service, e.g. "_node._tcp.local.".
        :type service_type: str
        :param name: The name of the service, e.g. "Node-X".
        :type name: str
        """
        info = zeroconf.get_service_info(service_type, name)
        if info:
            ip_list = info.parsed_addresses()
            for ip in ip_list:
                if ip != self.node.ip:
                    self.node.connect_to_peer(ip, info.port)

    def update_service(self,
                       zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange
                       ) -> None:
        """
        The `update_service` method is called by the `Zeroconf` instance when a service is added, removed,
        or updated on the network. It takes several arguments:

        :param zeroconf: A `Zeroconf` instance representing the local network.
        :type zeroconf: `Zeroconf`
        :param service_type: The type of the service that was updated, specified as a string in the format "<protocol>._<transport>.local." (e.g. "_node._tcp.local.").
        :type service_type: `str`
        :param name: The name of the service that was updated, as a string.
        :type name: `str`
        :param state_change: An enum indicating the type of change that occurred, one of "Added", "Updated", or "Removed".
        :type state_change: `ServiceStateChange`

        If the `state_change` is "Added" or "Updated", the method calls the `add_service` method to add the updated
        service to the network. Otherwise, the service is removed from the network.
        """
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
        """
        Initialize a new Node object.

        :param str name: The name of the node, e.g. "Node-X".
        :raises ValueError: If the provided name is empty or None.
        :raises socket.gaierror: If the IP address of the current machine cannot be determined.
        """
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
        """
        Start the node by parsing command line arguments, registering the node service with Zeroconf, and starting a
        thread to handle reconnections.

        :return: None
        """
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
        """
        The ``run`` method starts the node and its services. It initializes a ``ServiceBrowser`` to search for available
        nodes on the local network and starts a thread to accept incoming connections. If the program receives a
        keyboard interrupt signal, it will stop and exit gracefully.

        :return: None
        """

        try:
            print("Searching new nodes on local network..")
            browser = ServiceBrowser(self.zeroconf, "_node._tcp.local.", [self.listener.update_service])
            browser.start()
            threading.Thread(target=self.accept_connections).start()
        except KeyboardInterrupt:
            self.broadcast_message("Shutting down")
            self.stop()

    def accept_connections(self):
        """
        The ``accept_connections`` is a method that listens for incoming connections on the node's socket. It runs in
        a loop as long as the node is running. When a new connection is established, the method starts a new thread
        to handle incoming messages.

        :return: None

        """
        while self.running:
            conn, addr = self.socket.accept()
            print(f"Connected to {addr[0]}:{addr[1]}")

            # Start a thread to handle incoming messages
            threading.Thread(target=self.handle_messages, args=(conn,)).start()

    def validate(self, ip, port):
        """
        The ``validate`` method checks if a given IP address and port number are already in use by any of the
        existing connections in the node. If the IP address and port number are unique, the method returns True.
        Otherwise, it returns False.

        :param ip: The IP address to validate.
        :param port: The port number to validate.
        :return: True if the IP address and port number are unique, False otherwise.
        """
        flag = True
        for connection in self.connections:
            if ip != connection.getpeername()[0] and port != connection.getpeername()[1]:
                flag = True
            else:
                flag = False
        return flag

    def handle_reconnects(self):
        """
        The ``handle_reconnects`` method is a background thread that monitors the node's connections and attempts to
        reconnect if there are no active connections. The method also broadcasts a message to all connected nodes if
        the node recently reconnected.
        :return: None
        """
        while self.running:
            if len(self.connections) < 1 and self.recon_state is True:
                # If there are no connections and reconnection is required, update the node's last seen time and wait
                # for the specified amount of time before attempting to reconnect
                self.blockchain.nodes[self.ip] = time.time()
                print("Attempting to reconnect...")
                time.sleep(self.keep_alive_timeout)
            elif len(self.connections) > 0 and self.recon_state is True:
                # If there are active connections and reconnection is required, broadcast a "BC" message to all nodes
                # and wait for a short amount of time before continuing
                self.recon_state = False
                self.broadcast_message("BC")
                time.sleep(2)
                continue

    def connect_to_peer(self, client_host, client_port):
        """
        The `connect_to_peer` method is used to create a socket connection with the specified client. If the specified
        client is already connected, it will not create a new connection. It adds a new node by creating a socket connection
        to the specified client and adds it to the node list. Additionally, it starts threads to handle incoming messages and
        to send keep-alive messages.

        :param client_host: The host address of the client to connect to, e.g. [192.168.X.X].
        :param client_port: The port number of the client to connect to, e.g. [5000].
        :return: None
        """
        if self.validate(client_host, client_port) is not True or self.ip == client_host:
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

                handle_messages = threading.Thread(target=self.handle_messages, args=(conn,))
                handle_messages.start()

                send_keep_alive_msg = threading.Thread(target=self.send_keep_alive_messages, args=(conn,))
                send_keep_alive_msg.start()

                break
            except ConnectionRefusedError:
                print(f"Connection refused by {client_host}:{client_port}, retrying in 10 seconds...")
                time.sleep(10)

    def send_keep_alive_messages(self, conn):
        """
        The ``send_keep_alive_messages`` method sends a "ping" message to the specified connection periodically
        to maintain the connection. If the connection fails or is closed, it will remove the node from the list.

        :param conn: The connection object to send the keep-alive messages to.
        :return: None
        """

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
        """
        The ``handle_messages`` method handles incoming messages from a peer node. It listens for messages on the
        connection object and responds to them appropriately. If the received message is "ping", it sends a "pong"
        message to keep the connection alive. If the message is empty, it updates the node's priority and breaks the
        loop. If there is a socket timeout or OSError, the method sets the ``recon_state`` flag to True and removes
        the node from the list of connections. If the connection is reset, it also removes the node from the list
        and closes the connection.

        :param conn: socket connection object representing the connection to the peer node
        :type conn: socket.socket
        :return: None
        """
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
        """
        The ``broadcast_message`` method broadcasts a message to all connected peers. The message is encoded and sent to
        each peer using the ``sendall`` method of the socket object.

        :param message: str, the message to be broadcast
        :return: None
        """
        for peer in self.connections:
            peer.sendall(message.encode())

    def list_peers(self):
        """Prints a list of all connected peers.

        Prints the IP address and port number of each connected peer, using the format:
        [<index>] <IP address>:<port number>

        :return: None
        """
        print("\n\nPeers:")
        for i, conn in enumerate(self.connections):
            print(f"[{i}] <{conn.getpeername()[0]}:{conn.getpeername()[1]}>")
        print("\n\n")

    def stop(self):
        """
        The ``stop`` method stop the server and close the zeroconf connection.
        :return: None
        """
        self.running = False
        self.zeroconf.close()

    def add_node(self, conn):
        """
        The ``add_node`` method checks if the node is already in the list of connections, if the node is not in the list
        of connections add the new node to the blockchain network and to the list of node peer connections.

        :param conn: A socket connection object representing the new node to be added.
        :type conn: socket.socket
        :return: None
        """
        # Check if the node is already in the list of connections
        for connections in self.connections:
            if connections.getpeername()[0] == conn.getpeername()[0]:
                return

        # If the node is not in the list of connections, add it
        if conn not in self.connections:
            self.connections.append(conn)
            self.blockchain.register_node({conn.getpeername()[0]: time.time()})
            print(f"Node {conn.getpeername()[0]} added to the network")
            print(f"Nodes in Blockchain: [IP:TIMESTAMP]{self.blockchain.nodes}")

    def remove_node(self, conn, function):
        """
        The ``remove_node`` method removes the specified node from the list of connections and prints the updated list.

        :param conn: A socket connection object representing the node to be removed.
        :type conn: socket.socket
        :param function: A string indicating the reason why the node is being removed.
        :type function: str
        :return: None
        """
        print(f"Removed by {function}")
        if conn in self.connections:
            print(f"Node {conn} removed from the network")
            self.connections.remove(conn)
        print(f"Nodes still available:")
        self.list_peers()
