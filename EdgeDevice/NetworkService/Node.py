import logging
import socket
import ssl
import threading
import time
import uuid
import soundfile as sf

from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf, IPVersion, NonUniqueNameException

# from EdgeDevice.InferenceService.audio import AudioInference
from EdgeDevice.BlockchainService.Blockchain import Blockchain
from EdgeDevice.NetworkService.MessageHandler import MessageHandler
from EdgeDevice.NetworkService.NodeListener import NodeListener
from EdgeDevice.utils.constants import Network, HOST_PORT
from EdgeDevice.utils.helper import (
    get_keys, get_tls_keys,
    get_interface_ip, validate
)

logger = logging.getLogger(__name__)


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
        self.ip = get_interface_ip()  # ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']
        self.port = HOST_PORT
        self.last_keep_alive = time.time()
        self.keep_alive_timeout = 20
        self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
        self.listener = NodeListener(self)
        self.messageHandler = MessageHandler(self)
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS)  # Create the socket with TLS encryption
        self.context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        cert, key = get_tls_keys()
        self.context.load_cert_chain(certfile=cert, keyfile=key)
        self.retries = 5
        self.context.check_hostname = False  # Disable hostname verification for the server-side
        self.context.verify_mode = ssl.CERT_NONE
        self.socket = self.context.wrap_socket(
            socket.socket(socket.AF_INET, socket.SOCK_STREAM),
            server_side=True,
        )
        node_number = int(self.name.split('-')[1].strip())
        self.local = 'SALA' if node_number % 2 == 0 else 'COZINHA' if node_number == 1 else 'QUARTO'
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', self.port))
        self.socket.listen(5)
        self.state = Network.FOLLOWER
        self.coordinator = None
        self.running = True
        self.neighbours = {self.id: {'IP': self.ip, 'PUBLIC_KEY': self.public_key, 'LOCAL': self.local}}
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
            properties={'IP': self.ip, 'ID': self.id, 'LOCAL': self.local},
        )
        self.blockchain.register_node({self.ip: time.time()})

    def run(self):
        """
        Start the node

        The ``run`` method starts the node by parsing command line arguments, registering the node service with
        Zeroconf, and starting a thread to handle reconnections.

        :return: None
        """
        logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(message)s')

        try:
            self.zeroconf.register_service(self.service_info)
        except NonUniqueNameException as n:
            logging.error(f"Non Unique Name Exception Error: {n.args}")

            self.zeroconf.update_service(self.service_info)

        try:
            logging.info("[DISCOVERY] Starting the discovery service . . .")
            browser = ServiceBrowser(self.zeroconf, "_node._tcp.local.", [self.listener.update_service])

            threading.Thread(target=self.accept_connections).start()

        except KeyboardInterrupt:
            logging.error(f"Machine {Network.HOST_NAME} is shutting down")
            self.stop()

        time.sleep(1)

        if len(self.connections) == 0:
            time.sleep(2)
            self.start_election()

        threading.Thread(target=self.handle_reconnects).start()

    def handle_detection(self):
        """

        :return:
        """
        audio_model = {
            'name': 'yamnet_retrained',
            'frequency': 16000,  # sample rate in Hz
            'duration': 0.96,  # duration of each input signal in seconds
            'threshold': 0.85  # confidence threshold for classification
        }

        # audio_inference = AudioInference(audio_model)
        # audio_file_path = '../RetrainedModels/audio/test_audios/136.wav'
        # waveform, _ = sf.read(audio_file_path, dtype='float32')

        # while self.running and self.coordinator == self.id:
        #     inferred_class = audio_inference.inference(waveform)
        #     self.blockchain.pending_transactions.append(inferred_class)
        #    break

    def handle_reconnects(self):
        """
        The ``handle_reconnects`` method is a background thread that monitors the node's connections and attempts to
        reconnect if there are no active connections. The method also broadcasts a message to all connected nodes if
        the node recently reconnected.
        :return: None
        """
        while self.running:
            if len(self.connections) < 1 and self.recon_state is True:
                self.blockchain.nodes[self.ip] = time.time()
                logging.info(f"Attempting to reconnect...")
                time.sleep(5)
            elif len(self.connections) > 0 and self.recon_state is True:
                logging.info(f"Coordinator not seen for a while. Starting new election...")
                self.coordinator = None
                self.start_election()
                self.recon_state = False
                continue

    def accept_connections(self):
        """
        The ``accept_connections`` is a method that listens for incoming connections on the node's socket. It runs in
        a loop as long as the node is running. When a new connection is established, the method starts a new thread
        to handle incoming messages.

        :return: None

        """
        while self.running:
            conn, addr = self.socket.accept()
            logging.info(f"[CONNECTION] Connected to {addr[0]}:{addr[1]}")
            threading.Thread(target=self.messageHandler.handle_messages, args=(conn,)).start()

    def connect_to_peer(self, client_host, client_port, client_id, node_local):
        """
        The `connect_to_peer` method is used to create a TLS-encrypted socket connection with the specified client.
        If the specified client is already connected, it will not create a new connection. It adds a new node by
        creating a socket connection to the specified client and adds it to the node list. Additionally,
        it starts threads to handle incoming messages and to send keep-alive messages.

        :param node_local: The local where the node is set.
        :param client_id: The ID of the new node.
        :type client_id: <bytes>
        :param client_host: The host address of the client to connect to, e.g. [192.168.X.X].
        :type client_host: <str>
        :param client_port: The port number of the client to connect to, e.g. [5000].
        :type client_port: <int>
        :return: None
        """

        logging.info(f"[CONNECTION] Node Information: {client_host, client_port, client_id, node_local}")

        if validate(self.connections, client_host, client_port) is not True or self.ip == client_host:
            logging.info(f"[CONNECTION] Already connected to {client_host, client_port, client_id, node_local}")
            return

        while self.running:
            try:
                conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

                context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)  # Wrap the socket with TLS encryption
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                conn = context.wrap_socket(conn, server_hostname=client_host)
                conn.connect((client_host, client_port))
                conn.settimeout(self.keep_alive_timeout * 3)

                self.add_node(conn, client_id, node_local)
                self.list_peers()

                time.sleep(1)

                handle_messages = threading.Thread(target=self.messageHandler.handle_messages, args=(conn,))
                handle_messages.start()

                time.sleep(1)

                handle_keep_alive_messages = threading.Thread(target=self.messageHandler.handle_keep_alive_messages,
                                                              args=(conn, client_id))
                handle_keep_alive_messages.start()

                handle_keep_alive_messages.join()
                handle_messages.join()

                break
            except ConnectionRefusedError as e:
                logging.error(f"[CONNECTION] Connection refused by {client_host}:{client_port}: {e.strerror}")
                time.sleep(5)

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
                        higher_nodes.append(neighbour['IP'])
                if higher_nodes:
                    for ip in higher_nodes:
                        for node in self.connections:
                            if node.getpeername()[0] == ip:
                                logging.info(f"[ELECTION] Node {self.ip} sent ELECTION message to {ip}")
                else:
                    self.coordinator = self.id
                    logging.info(f"[ELECTION] Node {self.id} is the new coordinator")
                    self.election_in_progress = False
            elif self.coordinator is None and len(self.connections) <= 0:
                self.coordinator = self.id
                # self.handle_detection()
                self.blockchain.add_block(self.blockchain.new_block())
                logging.info(f"[ELECTION] Node {self.id} is the coordinator.")
        except ssl.SSLZeroReturnError as e:
            logging.error(f"SSLZero Return Error {e.strerror}")
            return

    def broadcast_message(self, message):
        """
        The ``broadcast_message`` method broadcasts a message to all connected peers. The message is encoded and sent to
        each peer using the ``sendall`` method of the socket object.

        :param message: The message to be broadcast
        :type message: <str>
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

    def add_node(self, conn, client_id, node_local):
        """
        The ``add_node`` method checks if the node is already in the list of connections, if the node is not in the list
        of connections add the new node to the BlockchainService network and to the list of node peer connections.

        :param node_local: The local where the node is set
        :param client_id:The ID of the new node.
        :type client_id: <bytes>
        :param conn: A socket connection object representing the new node to be added.
        :type conn: <socket.socket>
        :return: None
        """
        for connections in self.connections:
            if connections.getpeername()[0] == conn.getpeername()[0]:
                return
        client_id = client_id.decode('utf-8')
        node_local = node_local.decode('utf-8')
        if conn not in self.connections:
            self.connections.append(conn)
            self.blockchain.register_node({conn.getpeername()[0]: time.time()})

            new_client_id = uuid.UUID(client_id)
            new_ip = conn.getpeername()[0]
            new_public_key = None
            self.neighbours[new_client_id] = {'IP': new_ip, 'PUBLIC_KEY': new_public_key, 'LOCAL': node_local}

            logging.info(f"Node [{conn.getpeername()[0]}] added to the network")
            logging.info(f"Nodes in Blockchain: [IP:TIMESTAMP]{self.blockchain.nodes}")

    def remove_node(self, conn, function):
        """
        The ``remove_node`` method removes the specified node from the list of connections and prints the updated list.

        :param conn: A socket connection object representing the node to be removed.
        :type conn: <socket.socket>
        :param function: A string indicating the reason why the node is being removed.
        :type function: <str>
        :return: None
        """
        logging.info(f"Removed by {function}")
        if conn in self.connections:
            logging.info(f"Node {conn} removed from the network")
            self.connections.remove(conn)
        logging.info(f"Nodes still available:")
        self.list_peers()
