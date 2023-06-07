import argparse
import logging
import random
import socket
import threading
import time
import ssl
import uuid
import netifaces as ni
from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf, IPVersion, NonUniqueNameException
from EdgeDevice.BlockchainService.Blockchain import Blockchain
from EdgeDevice.NetworkService.NodeListener import NodeListener
from EdgeDevice.BlockchainService.Transaction import validate_transaction
from EdgeDevice.NetworkService.Messages import meta
from EdgeDevice.utils.constants import Network, HOST_PORT, BUFFER_SIZE
import json
from EdgeDevice.utils.helper import get_keys, get_tls_keys, load_public_key_from_json, public_key_to_json


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
        self.private_key, self.public_key = get_keys()
        self.name = name
        self.ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
        self.port = HOST_PORT
        self.last_keep_alive = time.time()
        self.keep_alive_timeout = 20
        self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
        self.listener = NodeListener(self)
        # Create the socket with TLS encryption
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        self.context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        cert, key = get_tls_keys()
        self.context.load_cert_chain(certfile=cert, keyfile=key)
        self.retries = 5
        # Disable hostname verification for the server-side socket
        self.context.check_hostname = False
        self.context.verify_mode = ssl.CERT_NONE

        self.socket = self.context.wrap_socket(
            socket.socket(socket.AF_INET, socket.SOCK_STREAM),
            server_side=True,
        )

        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', self.port))
        self.socket.listen(5)

        self.state = Network.FOLLOWER
        self.coordinator = None
        self.running = True
        self.neighbours = {self.id: {'ip': self.ip, 'public_key': self.public_key}}
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

        time.sleep(1)

        # threading.Thread(target=self.handle_detection).start()

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

    def connect_to_peer(self, client_host, client_port, client_id):
        """
        The `connect_to_peer` method is used to create a TLS-encrypted socket connection with the specified client.
        If the specified client is already connected, it will not create a new connection. It adds a new node by
        creating a socket connection to the specified client and adds it to the node list. Additionally,
        it starts threads to handle incoming messages and to send keep-alive messages.

        :param client_id: The ID of the new node.
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
                # Create a TCP socket
                conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

                # Wrap the socket with TLS encryption
                context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                conn = context.wrap_socket(conn, server_hostname=client_host)

                # Connect to the peer using the TLS-encrypted socket
                conn.connect((client_host, client_port))
                conn.settimeout(60.0)

                # Continue with the rest of your code
                self.add_node(conn, client_id)
                self.list_peers()

                handle_messages = threading.Thread(target=self.handle_messages, args=(conn,))
                handle_messages.start()

                time.sleep(1)

                handle_keep_alive_messages = threading.Thread(target=self.handle_keep_alive_messages,
                                                              args=(conn, client_id))
                handle_keep_alive_messages.start()

                break
            except ConnectionRefusedError:
                print(f"Connection refused by {client_host}:{client_port}, retrying in 10 seconds...")
                time.sleep(10)

    def handle_keep_alive_messages(self, conn, client_id):
        """
        The ``handle_keep_alive_messages`` method sends keep-alive messages to the specified connection periodically
        to maintain the connection. The keep-alive message
        includes information such as the sender's metadata, message type, last time alive, coordinator information, and
        public key. If an exception occurs during the process, the function breaks the loop and closes the connection.

        :param conn: Socket connection object representing the connection to the peer node.
        :type conn: socket.socket
        :param client_id: The unique identifier of the connected peer node.
        :type client_id: bytes
        :return: None
        """

        while self.running:
            try:
                data = {
                    "META": meta(str(self.id), self.ip, self.port, conn.getpeername()[0], conn.getpeername()[1],
                                 str(client_id.decode('utf-8'))),
                    "TYPE": "PING",
                    "PAYLOAD": {
                        "LAST_TIME_ALIVE": time.time(),
                        "COORDINATOR": str(self.coordinator),
                    }
                }

                neighbour_id = uuid.UUID(client_id.decode('utf-8'))
                neighbour = self.neighbours.get(neighbour_id)
                if neighbour is not None and neighbour['public_key'] is None:
                    print("Public Key is None adding Public Key on PAYLOAD")
                    data["PAYLOAD"]["PUBLIC_KEY"] = public_key_to_json(self.public_key)
                print(f"Public Key is {neighbour['public_key']}")
                # Convert JSON data to string
                message = json.dumps(data, indent=2)
                conn.send(bytes(message, encoding="utf-8"))
                time.sleep(self.keep_alive_timeout)
            except Exception as ex:  # Catch the specific exception you want to handle
                print(f"Exception error in Keep Alive: {ex.args}")
                break

        # close connection and remove node from list
        if conn in self.connections:
            self.recon_state = True
            self.remove_node(conn, "KAlive")
            client_id_str = client_id.decode('utf-8')
            client_uuid = uuid.UUID(client_id_str)
            if client_uuid in self.neighbours:
                self.neighbours.pop(client_uuid)
            conn.close()

    def start_election(self):
        """
        The ``start_election`` method implements the Bully algorithm that is a centralized leader election algorithm.
        In this algorithm, nodes with higher IDs bully nodes with lower IDs to become the leader. When a node detects
        that the leader is unresponsive, it initiates an election by sending election messages to higher-ID nodes. If
        no higher-ID node responds, the node becomes the leader. If a higher-ID node responds, it withdraws from the
        election. The process continues until a leader is elected.

        :return: None
        """
        try:
            if self.coordinator is None and len(self.connections) > 0:
                pass
                self.election_in_progress = True
                higher_nodes = []
                for neighbour_id, neighbour in self.neighbours.items():
                    if neighbour_id > self.id:
                        higher_nodes.append(neighbour['ip'])
                if higher_nodes:
                    for ip in higher_nodes:
                        for node in self.connections:
                            if node.getpeername()[0] == ip:
                                print(f"Node {self.ip} sent ELECTION message to {ip}")

                else:
                    self.coordinator = self.id
                    self.broadcast_message(f"COORDINATOR {self.coordinator}")
                    print(f"Node {self.id} is the new coordinator")
                    self.election_in_progress = False
            elif self.coordinator is None and len(self.connections) <= 0:
                self.coordinator = self.id
                print(f"Node {self.id} is the coordinator")
        except ssl.SSLZeroReturnError as e:
            print(f"SSLZero Return Error {e.strerror}")
            return

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
                self.recon_state = False
                continue

    def handle_messages(self, conn):
        """

        The ``handle_messages`` method handles incoming messages from a peer node. It listens for messages on the
        connection object and responds to them appropriately. If the received message is a valid JSON message,
        it extracts the message type and processes it accordingly. If the message is empty, it updates the node's
        priority and breaks the loop. If there is a socket timeout or OSError, the method sets the ``recon_state``
        flag to True and removes the node from the list of connections. If the connection is reset, it also removes
        the node from the list and closes the connection.

        :param conn: socket connection object representing the connection to the peer node
        :type conn: socket.socket
        :return: None
        """
        while self.running:
            try:
                data = conn.recv(BUFFER_SIZE).decode()
                message = json.loads(data)
                print(message)
                message_type = message.get("TYPE")
                if message_type == "PING":
                    if self.coordinator is None:
                        self.coordinator = uuid.UUID(message["PAYLOAD"].get("COORDINATOR"))
                        print(f"\nNetwork Coordinator is {self.coordinator}\n")
                    print(message_type)

                    neighbour_id = uuid.UUID(message['META']['FROM_ADDRESS']['ID'])
                    neighbour = self.neighbours.get(neighbour_id)
                    self.retries = 5
                    if neighbour is not None and neighbour['public_key'] is None:
                        # Extract the base64-encoded public key from the received message
                        public_key_base64 = message['PAYLOAD']['PUBLIC_KEY']

                        # Decode the base64-encoded public key back to bytes
                        public_key = load_public_key_from_json(public_key_base64)
                        if public_key is not None:
                            # Update public key for the specific IP address in the dictionary
                            self.neighbours[neighbour_id]['public_key'] = public_key

                    data = {
                        "META": meta(str(self.id), self.ip, self.port, conn.getpeername()[0], conn.getpeername()[1],
                                     str(neighbour_id)),
                        "TYPE": "PONG",
                        "PAYLOAD": {
                            "LAST_TIME_ALIVE": time.time(),
                            "COORDINATOR": str(self.coordinator),
                        }
                    }

                    print(self.neighbours, "\n")

                    message_json = json.dumps(data, indent=2)
                    conn.send(bytes(message_json, encoding="utf-8"))

                if message_type == "TRANSACTION":
                    # Validate the transaction
                    tx = message["PAYLOAD"].get("TRANSACTION_MESSAGE")

                    if validate_transaction(tx) is True:
                        # Add the tx to our pool, and propagate it to our peers
                        if tx not in self.blockchain.pending_transactions:
                            self.blockchain.pending_transactions.append(tx)
                            data = {
                                "META": meta(str(self.id), self.ip, self.port, conn.getpeername()[0],
                                             conn.getpeername()[1]),
                                "TYPE": "TRANSACTION",
                                "PAYLOAD": {
                                    "COORDINATOR": str(self.coordinator),
                                    "BLOCKCHAIN": self.blockchain.chain,
                                    "TRANSACTION_MESSAGE": tx,
                                }
                            }
                            message = json.dumps(data, indent=2)
                            self.broadcast_message(message)
                    else:
                        print("Received invalid transaction")
                        continue

                if message_type == "BLOCK":
                    pass

                if not data:
                    self.service_info.priority = random.randint(1, 100)
                    self.zeroconf.update_service(self.service_info)
                    break

            except json.JSONDecodeError as e:
                print("Error decoding JSON:", e)
                print(f"Retrying attempts left {self.retries}...")
                self.retries -= 1
                time.sleep(1)
                if self.retries <= 0:
                    break

            except ssl.SSLZeroReturnError as e:
                print(f"SSLZero Return Error {e.strerror}")
                break

            except socket.timeout as e:
                print("Error timeout:", e)
                self.recon_state = True
                if conn in self.connections:
                    self.remove_node(conn, "Timeout")
                    conn.close()
                break

            except ConnectionResetError as c:
                print(f"Connection Reset Error {c.strerror}")
                if conn in self.connections:
                    self.remove_node(conn, "ConnectionResetError")
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

    def get_public_key_by_ip(self, ip_address):
        for neighbour_id, neighbour_info in self.neighbours.items():
            if neighbour_info['ip'] == ip_address:
                return neighbour_info['public_key']
        return None

    def broadcast_message(self, message):
        """
        The ``broadcast_message`` method broadcasts a message to all connected peers. The message is encoded and sent to
        each peer using the ``sendall`` method of the socket object.

        :param message: The message to be broadcast
        :type message: str
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
            new_client_id = uuid.UUID(client_id)
            new_ip = conn.getpeername()[0]
            new_public_key = None

            self.neighbours[new_client_id] = {'ip': new_ip, 'public_key': new_public_key}

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
