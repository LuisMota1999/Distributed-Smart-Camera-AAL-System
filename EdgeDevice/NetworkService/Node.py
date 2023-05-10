import argparse
import logging
import random
import socket
import threading
import time
from asyncio.log import logger
from typing import cast
import uuid
import netifaces as ni
from marshmallow.exceptions import MarshmallowError
from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf, ServiceStateChange, IPVersion, \
    NonUniqueNameException
from EdgeDevice.BlockchainService.Blockchain import Blockchain
from EdgeDevice.BlockchainService.Transaction import validate_transaction
from EdgeDevice.NetworkService.Messages import create_transaction_message, create_block_message, BaseSchema, \
    create_ping_message, create_election_message
from EdgeDevice.utils.constants import Network, HOST_PORT
import json
import asyncio


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
                    self.node.connect_to_peer(ip, info.port, info.properties.get(b'ID'))

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
        self.id = uuid.uuid4()
        self.name = name
        self.ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
        self.port = HOST_PORT
        self.last_seen = time.time()
        self.keep_alive_timeout = 10
        self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
        self.listener = NodeListener(self)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', self.port))
        self.socket.listen(5)
        self.state = Network.FOLLOWER
        self.coordinator = None
        self.running = True
        self.neighbours = {self.id: self.ip}
        self.connections = []
        self.blockchain = Blockchain()
        self.recon_state = False
        self.election_in_progress = False
        self.service_info = ServiceInfo(
            type_="_node._tcp.local.",
            name=f"{self.name}._node._tcp.local.",
            addresses=[socket.inet_aton(self.ip)],
            port=HOST_PORT,
            weight=0,
            priority=0,
            properties={'IP': self.ip, 'ID': self.id},
        )

        self.blockchain.register_node({self.ip: time.time()})

    def run(self):
        """
        Start the node

        The ``run`` method starts the node by parsing command line arguments, registering the node service with
        Zeroconf, and starting a thread to handle reconnections.

        :return: None
        """

        parser = argparse.ArgumentParser()
        parser.add_argument('--debug', action='store_true')
        parser.add_argument('--find', action='store_true', help='Browse all available services')
        parser.add_argument('-src', '--source', dest='video_source', type=int,
                            default=0, help='Device index of the camera.')
        parser.add_argument('-wd', '--width', dest='width', type=int,
                            default=480, help='Width of the frames in the video stream.')
        parser.add_argument('-ht', '--height', dest='height', type=int,
                            default=360, help='Height of the frames in the video stream.')
        parser.add_argument('-num-w', '--num-workers', dest='num_workers', type=int,
                            default=4, help='Number of workers.')
        parser.add_argument('-q-size', '--queue-size', dest='queue_size', type=int,
                            default=5, help='Size of the queue.')
        version_group = parser.add_mutually_exclusive_group()
        version_group.add_argument('--v6', action='store_true')
        version_group.add_argument('--v6-only', action='store_true')
        args = parser.parse_args()

        if args.debug:
            logging.getLogger('NetworkService').setLevel(logging.DEBUG)

        try:
            self.zeroconf.register_service(self.service_info)
        except NonUniqueNameException:
            self.zeroconf.update_service(self.service_info)

        try:
            print("[COORDINATOR] Starting the discovery service...")
            browser = ServiceBrowser(self.zeroconf, "_node._tcp.local.", [self.listener.update_service])
            threading.Thread(target=self.accept_connections).start()
        except KeyboardInterrupt:
            print(f"Machine {Network.HOST_NAME} is shutting down...")
            self.stop()

        time.sleep(1)

        self.start_election()

        threading.Thread(target=self.handle_reconnects).start()

    def discovery_service(self):
        """
        The method ``discovery_service`` initializes a ``ServiceBrowser`` to search for
        available nodes on the local network if the node is the coordinator. If the program
        receives a keyboard interrupt signal, it will stop and exit gracefully.
        :return: None
        """
        while self.running:
            if self.coordinator == self.id:
                break

        try:
            print("[COORDINATOR] Starting the discovery service...")
            browser = ServiceBrowser(self.zeroconf, "_node._tcp.local.", [self.listener.update_service])
        except KeyboardInterrupt:
            print(f"Machine {Network.HOST_NAME} is shutting down...")
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
        :type ip: str
        :param port: The port number to validate.
        :type port: int
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
                print("Coordinator not seen for a while. Starting new election...")
                self.coordinator = None
                self.start_election()
                # Blockchain message
                data = {"TYPE": "BLOCKCHAIN", "DATA": self.blockchain.to_json()}
                # Convert JSON data to string
                message = json.dumps(data)
                self.broadcast_message(message)
                self.recon_state = False
                continue

    def connect_to_peer(self, client_host, client_port, client_id):
        """
        The `connect_to_peer` method is used to create a socket connection with the specified client. If the
        specified client is already connected, it will not create a new connection. It adds a new node by creating a
        socket connection to the specified client and adds it to the node list. Additionally, it starts threads to
        handle incoming messages and to send keep-alive messages.

        :param client_id:The ID of the new node.
        :type client_id: bytes
        :param client_host: The host address of the client to connect to, e.g. [192.168.X.X].
        :type client_host: str
        :param client_port: The port number of the client to connect to, e.g. [5000].
        :type client_port: int
        :return: None
        """
        if self.validate(client_host, client_port) is not True or self.ip == client_host:
            print(f"Already connected to {client_host, client_port, client_id}")
            return

        while self.running:
            try:
                conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                conn.connect((client_host, client_port))
                conn.settimeout(self.keep_alive_timeout * 3)

                self.add_node(conn, client_id)
                self.list_peers()

                # if self.coordinator == self.id: peer_info = {"ip": self.ip, "port": self.port, "id": str(self.id),
                # "coordinator": self.coordinator} peer_info = json.dumps(peer_info) peer_info = f"CONNECT{
                # peer_info}" conn.sendto(peer_info.encode(), (client_host, client_port))

                handle_messages = threading.Thread(target=self.handle_messages, args=(conn,))
                handle_messages.start()

                time.sleep(5)

                send_keep_alive_msg = threading.Thread(target=self.send_keep_alive_messages, args=(conn, client_id))
                send_keep_alive_msg.start()

                break
            except ConnectionRefusedError:
                print(f"Connection refused by {client_host}:{client_port}, retrying in 10 seconds...")
                time.sleep(10)

    def send_keep_alive_messages(self, conn, client_id):
        """
        The ``send_keep_alive_messages`` method sends a "ping" message to the specified connection periodically
        to maintain the connection. If the connection fails or is closed, it will remove the node from the list.

        :param client_id: The ID of the new node.
        :type client_id: bytes
        :param conn: The connection object to send the keep-alive messages to.
        :type conn: socket.socket
        :return: None
        """

        while self.running:
            try:
                conn.send(
                    create_ping_message(self.ip, self.port, len(self.blockchain.chain), 1, 1,
                                        "PING", self.coordinator).encode())

                time.sleep(self.keep_alive_timeout)
            except:
                break

        # close connection and remove node from list
        if conn in self.connections:
            self.recon_state = True
            self.remove_node(conn, "KeepAlive")
            client_id = client_id.decode('utf-8')
            self.neighbours.pop(uuid.UUID(client_id))
            conn.close()

    def start_election(self):
        """
        The ``start_election`` method start the election among the nodes in the network. Sets the node with higher uid
        the coordinator.

        :return: None
        """
        if self.coordinator is None and len(self.connections) > 0:
            self.election_in_progress = True
            higher_nodes = []
            for neighbour_id, neighbour in self.neighbours.items():
                if neighbour_id > self.id:
                    higher_nodes.append(neighbour)
            if higher_nodes:
                for ip in higher_nodes:
                    for node in self.connections:
                        if node.getpeername()[0] == ip:
                            print(f"Node {self.ip} sent election message to {ip}")

            else:
                self.coordinator = self.id

                #self.broadcast_message(create_election_message(self.ip, self.port, self.coordinator))
                print(f"Node {self.id} is the new coordinator")
                self.election_in_progress = False
        elif self.coordinator is None and len(self.connections) <= 0:
            self.coordinator = self.id
            print(f"Node {self.id} is the coordinator")

    def handle_blockchain(self, message, conn):
        pass

    def handle_ping(self, message, conn):
        print("\n\n\nCHEGUEI HANDLE PING\n\n\n")
        if self.coordinator is None:
            self.coordinator = message["MESSAGE"]["PAYLOAD"]["COORDINATOR"]
            self.election_in_progress = False
            print(f"\nNetwork Coordinator is {self.coordinator}\n")
            # conn.send(create_block_message(str(conn.getpeername()[0]), conn.getpeername()[1], message))

        conn.send(
            create_ping_message(self.ip, self.port, len(self.blockchain.chain), 1, 1,
                                "PONG", self.coordinator).encode())

    def handle_election(self, message, conn):
        pass

    def handle_transaction(self, message, conn):
        """
        Executed when we receive a transaction that was broadcast by a peer
        """
        logger.info("Received transaction")

        # Validate the transaction
        tx = message["PAYLOAD"]

        if validate_transaction(tx) is True:
            # Add the tx to our pool, and propagate it to our peers
            if tx not in self.blockchain.pending_transactions:
                self.blockchain.pending_transactions.append(tx)
                self.broadcast_message(create_block_message(conn.getpeername()[0], conn.getpeername()[1], tx))
        else:
            logger.warning("Received invalid transaction")

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

                data = conn.recv(1024).decode()
                try:
                    print(BaseSchema().loads(data))
                    message = BaseSchema().loads(data)
                except MarshmallowError:
                    logger.info("Received unreadable message", peer=conn)
                    print("Received unreadable message")
                    continue

                message_handlers = {
                    "BLOCK": threading.Thread(self.handle_blockchain(message, conn)).start(),
                    "PING": threading.Thread(self.handle_ping(message, conn)).start(),
                    "ELECTION": threading.Thread(self.handle_election(message, conn)).start(),
                    "TRANSACTION": threading.Thread(self.handle_transaction(message, conn)).start(),
                }

                handler = message_handlers.get(message["NAME"])

                if not handler:
                    raise Exception("Missing handler for message")

                if not data:
                    self.service_info.priority = random.randint(1, 100)
                    self.zeroconf.update_service(self.service_info)
                    break

            except socket.timeout:
                print("Timeout")
                self.recon_state = True
                if conn in self.connections:
                    self.remove_node(conn, "Timeout")
                    conn.close()
                break

            except OSError as e:
                print(f"System Error {e.strerror}")
                break

            except Exception as ex:
                print(f"Exception Error {ex.args}")
                break

            except ConnectionResetError as c:
                print(f"Connection Reset Error {c.strerror}")
                if conn in self.connections:
                    self.remove_node(conn, "ConnectionResetError")
                    conn.close()
                break

            except json.decoder.JSONDecodeError:
                print("Invalid message format")
                break

    def broadcast_message(self, message):
        """
        The ``broadcast_message`` method broadcasts a message to all connected peers. The message is encoded and sent to
        each peer using the ``sendall`` method of the socket object.

        :param message: The message to be broadcast
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
        The ``stop`` method stop the server and close the NetworkService connection.
        :return: None
        """
        self.running = False
        self.zeroconf.close()

    def add_node(self, conn, client_id):
        """
        The ``add_node`` method checks if the node is already in the list of connections, if the node is not in the list
        of connections add the new node to the BlockchainService network and to the list of node peer connections.

        :param client_id:The ID of the new node.
        :type client_id: bytes
        :param conn: A socket connection object representing the new node to be added.
        :type conn: socket.socket
        :return: None
        """
        # Check if the node is already in the list of connections
        for connections in self.connections:
            if connections.getpeername()[0] == conn.getpeername()[0]:
                return
        client_id = client_id.decode('utf-8')
        # If the node is not in the list of connections, add it
        if conn not in self.connections:
            self.connections.append(conn)
            # Register the new node with the blockchain service
            self.blockchain.register_node({conn.getpeername()[0]: time.time()})

            # Add the new node to the dictionary of neighbors
            self.neighbours.update({uuid.UUID(client_id): conn.getpeername()[0]})

            # Print a message indicating that the new node has been added to the network
            print(f"Node {conn.getpeername()[0]} added to the network")

            # Print the list of nodes in the blockchain
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
