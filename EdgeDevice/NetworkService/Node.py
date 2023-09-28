import soundfile as sf
import logging
import random
import socket
import threading
import time
import ssl
import uuid
import json

from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf, IPVersion, NonUniqueNameException
from EdgeDevice.BlockchainService.Blockchain import Blockchain
from EdgeDevice.InferenceService.audio import AudioInference
from EdgeDevice.InferenceService.video import VideoInference, VideoClassifierOptions
from EdgeDevice.NetworkService.NodeListener import NodeListener
from EdgeDevice.HomeAssistantService.HomeAssistant import Homeassistant
from EdgeDevice.BlockchainService.Transaction import validate_transaction, create_transaction
from EdgeDevice.utils.constants import Network, HOST_PORT, BUFFER_SIZE, Messages, Transaction, Inference
from EdgeDevice.utils.helper import NetworkUtils, MessageHandlerUtils

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
        self.private_key, self.public_key = NetworkUtils.get_keys()
        self.name = name
        self.ip = NetworkUtils.get_interface_ip()
        self.port = HOST_PORT
        self.last_keep_alive = time.time()
        self.keep_alive_timeout = 10
        self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
        self.listener = NodeListener(self)
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        self.context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        cert, key = NetworkUtils.get_tls_keys()
        self.context.load_cert_chain(certfile=cert, keyfile=key)
        self.retries = 5
        self.context.check_hostname = False
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
        self.homeassistant_listener = Homeassistant()
        self.blockchain.register_node({self.ip: time.time()})

    def run(self):
        """
        Start the node

        The ``run`` method starts the node by parsing command line arguments, registering the node service with
        Zeroconf, and starting a thread to handle reconnections.

        :return: None
        """

        global handle_discovery
        global handle_connections
        try:
            self.zeroconf.register_service(self.service_info)
        except NonUniqueNameException as n:
            logging.error(f"Non Unique Name Exception Error: {n.args}")
            self.zeroconf.update_service(self.service_info)

        try:
            logging.info("[DISCOVERY] Starting the discovery service . . .")
            handle_discovery = ServiceBrowser(self.zeroconf, "_node._tcp.local.", [self.listener.update_service])

            handle_connections = threading.Thread(target=self.accept_connections)
            handle_connections.start()
        except KeyboardInterrupt:
            logging.error(f"Machine {Network.HOST_NAME} is shutting down")
            self.stop()

        if len(self.connections) == 0:
            time.sleep(3)
            self.handle_election()

        time.sleep(2)

        handle_detection = threading.Thread(target=self.handle_detection)
        handle_detection.start()

        try:
            if not self.running:
                handle_detection.join()
                handle_discovery.join()
                handle_connections.join()
        except Exception as e:
            logging.error(f"Machine {Network.HOST_NAME} is shutting down with errors {e.args}")

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
        :type ip: <str>
        :param port: The port number to validate.
        :type port: <int>
        :return: True if the IP address and port number are unique, False otherwise.
        """
        flag = True
        for connection in self.connections:
            if ip != connection.getpeername()[0] and port != connection.getpeername()[1]:
                flag = True
            else:
                flag = False
        return flag

    def connect_to_peer(self, client_host, client_port, client_id, node_local):
        """
        The `connect_to_peer` method is used to create a TLS-encrypted socket connection with the specified client.
        If the specified client is already connected, it will not create a new connection. It adds a new node by
        creating a socket connection to the specified client and adds it to the node list. Additionally,
        it starts threads to handle incoming messages and to send keep-alive messages.

        :param node_local:
        :param client_id: The ID of the new node.
        :type client_id: <bytes>
        :param client_host: The host address of the client to connect to, e.g. [192.168.X.X].
        :type client_host: <str>
        :param client_port: The port number of the client to connect to, e.g. [5000].
        :type client_port: <int>
        :return: None
        """
        if self.validate(client_host, client_port) is not True or self.ip == client_host:
            logging.info(f"[CONNECTION] Already connected to {client_host, client_port, client_id, node_local}")
            return

        while self.running:
            try:
                conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 5)

                context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                conn = context.wrap_socket(conn, server_hostname=client_host)

                conn.connect((client_host, client_port))
                conn.settimeout(self.keep_alive_timeout * 3)

                handle_messages = threading.Thread(target=self.handle_messages, args=(conn,))
                handle_messages.start()

                self.add_node(conn, client_id, node_local)
                self.list_peers()

                handle_keep_alive_messages = threading.Thread(target=self.handle_keep_alive_messages,
                                                              args=(client_id,))
                handle_keep_alive_messages.start()

                handle_chain_messages = threading.Thread(target=self.handle_chain_message,
                                                         args=("", conn, client_id,
                                                               Messages.MESSAGE_TYPE_REQUEST_CHAIN.value))
                handle_chain_messages.start()
                break
            except ConnectionRefusedError:
                print(f"Connection refused by {client_host}:{client_port}, retrying in 10 seconds...")
                time.sleep(10)

    def handle_election(self):
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
                logging.info(f"[ELECTION] Node {self.id} is the coordinator.")
                self.blockchain.add_block(self.blockchain.new_block())
                self.homeassistant_listener.start()
        except ssl.SSLZeroReturnError as e:
            logging.error(f"SSLZero Return Error {e.strerror}")
            return

    def handle_detection(self):
        """
        Continuously handles audio detection and classification using a pre-trained audio and video model.

        This method initializes an audio model and performs audio inference on an audio file.
        It continuously monitors the audio waveform for detected classes, creates blockchain transactions for each
        detected class, and broadcasts the transaction information to the network.

        :return: None
        """
        audio_model = {
            'name': 'yamnet_retrained',
            'frequency': 16000,  # sample rate in Hz
            'duration': 0.96,  # duration of each input signal in seconds
            'threshold': 0.75  # confidence threshold for audio classification
        }

        video_model = {
            'model': Inference.VIDEO_MODEL.value,
            'resolution': 224,  # frame resolution
            'threshold': 0.75  # confidence threshold for video classification
        }

        audio_inference = AudioInference(audio_model)
        audio_file_path = f'../RetrainedModels/audio/test_audios/{self.name}/136.wav'
        waveform, _ = sf.read(audio_file_path, dtype='float32')

        options = VideoClassifierOptions(
            num_threads=Inference.VIDEO_NUM_THREADS.value, max_results=Inference.VIDEO_MAX_RESULTS.value,
            label_allow_list=Inference.VIDEO_ALLOW_LIST.value, label_deny_list=Inference.VIDEO_DENY_LIST.value)

        video_inference = VideoInference(Inference.VIDEO_MODEL.value, Inference.VIDEO_LABEL.value, options,
                                         video_model['threshold'])
        video_file_path = f'../RetrainedModels/video/test_videos/{self.name}/video.gif'

        last_audio_class = ""
        last_video_class = ""
        logging.info(f'Inference Starting')
        while self.running:
            inferred_audio_classes, top_score_audio = audio_inference.inference(waveform)
            inferred_video_classes, top_score_video = video_inference.inference(video_file_path)

            if top_score_audio < audio_model['threshold'] or top_score_video < video_model['threshold']:
                if len(self.blockchain.pending_transactions) > 0:
                    last_event_registered_bc = NetworkUtils.get_last_event_blockchain(
                        "EVENT_TYPE", self.blockchain.pending_transactions)
                    logging.info(f"Last Event Registered BC: {last_event_registered_bc}")
                else:
                    self.process_detection(inferred_audio_classes, inferred_video_classes, last_audio_class,
                                           last_video_class, audio_inference, video_inference, top_score_audio,
                                           top_score_video)
            else:
                self.process_detection(inferred_audio_classes, inferred_video_classes, last_audio_class,
                                       last_video_class, audio_inference, video_inference, top_score_audio,
                                       top_score_video)

                last_video_class = inferred_video_classes
                last_audio_class = inferred_audio_classes
                time.sleep(2)

    def process_detection(self, inferred_audio_classes, inferred_video_classes, last_audio_class, last_video_class,
                          audio_inference, video_inference, top_score_audio, top_score_video):
        if inferred_audio_classes != last_audio_class and last_video_class != inferred_video_classes:
            logging.info(
                f'[AUDIO - \'{audio_inference.model_name}\'] {inferred_audio_classes} ({top_score_audio})')
            logging.info(
                f'[VIDEO - \'{video_inference.model_name}\'] {inferred_video_classes} ({top_score_video})')
            transaction_with_signature = self.create_blockchain_transaction(inferred_audio_classes,
                                                                            'INFERENCE',
                                                                            self.local,
                                                                            Transaction.TYPE_AUDIO_INFERENCE.value,
                                                                            str(top_score_audio),
                                                                            )

            data = MessageHandlerUtils.create_transaction_message(
                Messages.MESSAGE_TYPE_RESPONSE_TRANSACTION.value, str(self.id))

            data["PAYLOAD"]["PENDING"] = [transaction_with_signature]
            message = json.dumps(data, indent=2)

            homeassistant_data = MessageHandlerUtils.create_homeassistant_message(str(self.id),
                                                                                  inferred_audio_classes,
                                                                                  self.local)

            if self.coordinator == self.id:
                self.homeassistant_listener.publish_message(homeassistant_data)
            self.broadcast_message(message)

    def handle_reconnects(self):
        """
        The ``handle_reconnects`` method is a background thread that monitors the node's connections and attempts to
        reconnect if there are no active connections. The method also broadcasts a message to all connected nodes if
        the node recently reconnected.
        :return: None
        """
        exp_backoff_time = 0
        while self.running:
            if len(self.connections) < 1 and self.recon_state is True:
                self.blockchain.nodes[self.ip] = time.time()
                print("Attempting to reconnect...")
                exp_backoff_time = self.keep_alive_timeout + exp_backoff_time
                time.sleep(exp_backoff_time)
            elif len(self.connections) > 0 and self.recon_state is True:
                print("Coordinator not seen for a while. Starting new election...")
                self.coordinator = None
                self.handle_election()
                self.recon_state = False
                break

    def handle_keep_alive_messages(self, client_id):
        """
        The ``handle_keep_alive_messages`` method sends keep-alive messages to the specified connection periodically
        to maintain the connection. The keep-alive message
        includes information such as the sender's metadata, message type, last time alive, coordinator information, and
        public key. If an exception occurs during the process, the function breaks the loop and closes the connection.

        :param client_id: The unique identifier of the connected peer node.
        :type client_id: <bytes>
        :return: None
        """
        neighbour_id = uuid.UUID(client_id.decode('utf-8'))
        neighbour = self.neighbours.get(neighbour_id)
        while self.running:
            try:
                data = MessageHandlerUtils.create_keep_alive_message(str(self.id), self.ip, self.port,
                                                                     str(neighbour_id), str(self.coordinator),
                                                                     Messages.MESSAGE_TYPE_PING.value)

                if neighbour is not None and neighbour['PUBLIC_KEY'] is None:
                    data["PAYLOAD"]["PUBLIC_KEY"] = NetworkUtils.key_to_json(self.public_key)

                time.sleep(2)
                message = json.dumps(data, indent=2)
                self.broadcast_message(message)
                time.sleep(self.keep_alive_timeout * 2.5)
            except socket.error as e:
                logging.error(f"Socket error: {e.args}")
                break

            except Exception as ex:
                logging.error(f"Exception error in Keep Alive: {ex.args}")
                break

    def handle_chain_message(self, message, conn, neighbour_id, message_type):
        """
        Handles incoming chain-related messages between nodes in the blockchain network.

        This method processes different types of chain messages based on their message type.
        It allows the current node to respond to requests for the blockchain or update its own blockchain
        based on received chain information.

        :param message: The incoming message data.
        :param conn: The connection object representing the connection with the sending node.
        :param neighbour_id: The ID of the neighboring node that sent the message.
        :param message_type: The type of the incoming message (request or response).

        :return: None
        """
        if message_type == Messages.MESSAGE_TYPE_REQUEST_CHAIN.value:
            if self.coordinator == self.id:
                data = MessageHandlerUtils.create_general_message(str(self.id), self.ip, self.port,
                                                                  conn.getpeername()[0],
                                                                  conn.getpeername()[1],
                                                                  str(neighbour_id), str(self.coordinator),
                                                                  Messages.MESSAGE_TYPE_RESPONSE_CHAIN.value)

                data["PAYLOAD"]["CHAIN"] = self.blockchain.chain

                message_json = json.dumps(data, indent=2)
                logging.info(f"CHAIN MESSAGE: {message_json}")
                conn.send(bytes(message_json, encoding="utf-8"))
        elif message_type == Messages.MESSAGE_TYPE_RESPONSE_CHAIN.value:
            self.blockchain.chain = message["PAYLOAD"].get("CHAIN")
            logging.info(f"IP: {self.ip} , CHAIN: {self.blockchain.chain}")
            logging.info("Blockchain chain was updated with information from coordinator")

    def handle_transaction_message(self, message, conn, neighbour_id, message_type):
        """
        Handles incoming transaction-related messages between nodes in the blockchain network.

        This method processes different types of transaction messages based on their message type.
        It allows the current node to respond to requests for pending transactions or validate and
        incorporate received transactions into its pending transaction pool.

        :param message: The incoming message data.
        :param conn: The connection object representing the connection with the sending node.
        :param neighbour_id: The ID of the neighboring node that sent the message.
        :param message_type: The type of the incoming message (request or response).

        :return: None
        """
        try:
            if message_type == Messages.MESSAGE_TYPE_REQUEST_TRANSACTION.value:
                for tx in self.blockchain.pending_transactions:
                    data = MessageHandlerUtils.create_transaction_message(
                        Messages.MESSAGE_TYPE_RESPONSE_TRANSACTION.value, str(neighbour_id))

                    data["PAYLOAD"]["PENDING"] = [tx]
                    message = json.dumps(data, indent=2)

                    # logging.info(f"Transaction message: {message}")

                    conn.send(bytes(message, encoding="utf-8"))

            elif message_type == Messages.MESSAGE_TYPE_RESPONSE_TRANSACTION.value:
                tx_list = message["PAYLOAD"]["PENDING"]

                if isinstance(tx_list, list):
                    for transaction_with_signature in tx_list:
                        tx = transaction_with_signature["DATA"]
                        signature = transaction_with_signature["SIGNATURE"]
                        if transaction_with_signature not in self.blockchain.pending_transactions:
                            if validate_transaction(tx, signature):
                                logging.info("[TRANSACTION] Transaction is valid")

                                self.blockchain.pending_transactions.append(transaction_with_signature)
                                logging.info(f"\nPending Transactions: {self.blockchain.pending_transactions}")
                            else:
                                logging.warning("Received invalid transaction")
                                return
                        else:
                            logging.warning(f"Transaction {tx} already in pending transactions!")
                else:
                    logging.warning("Invalid transaction format")

        except Exception as e:
            logging.error(f"Handle transaction message error: {e}")

    def handle_general_message(self, message, conn, neighbour_id, message_type=Messages.MESSAGE_TYPE_PONG.value):
        """
        Handles incoming general messages between nodes in the blockchain network.

        This method processes general messages exchanged between nodes and handles the coordination
        of network activities, such as setting the network coordinator and exchanging public keys.

        :param message: The incoming message data.
        :param conn: The connection object representing the connection with the sending node.
        :param neighbour_id: The ID of the neighboring node that sent the message.
        :param message_type: The type of the incoming message (default: PONG message type).

        :return: None
        """
        if self.coordinator is None:
            self.coordinator = uuid.UUID(message["PAYLOAD"].get("COORDINATOR"))

            logging.info(f"Network Coordinator is {self.coordinator}")

            message_type = Messages.MESSAGE_TYPE_REQUEST_TRANSACTION.value

        neighbour = self.neighbours.get(neighbour_id)
        if neighbour is not None and neighbour['PUBLIC_KEY'] is None:
            public_key_base64 = message['PAYLOAD']['PUBLIC_KEY']
            public_key = NetworkUtils.load_key_from_json(public_key_base64)
            if public_key is not None:
                self.neighbours[neighbour_id]['PUBLIC_KEY'] = public_key

        data = MessageHandlerUtils.create_general_message(str(self.id), self.ip, self.port, conn.getpeername()[0],
                                                          conn.getpeername()[1],
                                                          str(neighbour_id), str(self.coordinator), message_type)

        if neighbour is not None and neighbour['PUBLIC_KEY'] is None:
            data["PAYLOAD"]["PUBLIC_KEY"] = NetworkUtils.key_to_json(self.public_key)

        message_json = json.dumps(data, indent=2)
        conn.send(bytes(message_json, encoding="utf-8"))

    def handle_messages(self, conn):
        """

        The ``handle_messages`` method handles incoming messages from a peer node. It listens for messages on the
        connection object and responds to them appropriately. If the received message is a valid JSON message,
        it extracts the message type and processes it accordingly. If the message is empty, it updates the node's
        priority and breaks the loop. If there is a socket timeout or OSError, the method sets the ``recon_state``
        flag to True and removes the node from the list of connections. If the connection is reset, it also removes
        the node from the list and closes the connection.

        :param conn: socket connection object representing the connection to the peer node
        :type conn: <socket.socket>
        :return: None
        """
        while self.running:
            try:
                data = conn.recv(BUFFER_SIZE).decode()

                if not data:
                    logging.info(f"Data not found {data}")
                    self.service_info.priority = random.randint(1, 100)
                    self.zeroconf.update_service(self.service_info)
                    break

                message = json.loads(data)
                message_type = message.get("TYPE")

                if Messages.MESSAGE_TYPE_PING.value != message_type and Messages.MESSAGE_TYPE_PONG.value != message_type: logging.info(
                    f"[MESSAGE TYPE]: {message_type}")

                neighbour_id = uuid.UUID(message['META']['FROM_ADDRESS']['ID'])

                if message_type == Messages.MESSAGE_TYPE_REQUEST_TRANSACTION.value:
                    self.handle_transaction_message(message, conn, str(neighbour_id), message_type)

                elif message_type == Messages.MESSAGE_TYPE_RESPONSE_TRANSACTION.value:
                    self.handle_transaction_message(message, conn, str(neighbour_id), message_type)

                elif message_type == Messages.MESSAGE_TYPE_REQUEST_CHAIN.value:
                    self.handle_chain_message(message, conn, str(neighbour_id), message_type)

                elif message_type == Messages.MESSAGE_TYPE_RESPONSE_CHAIN.value:
                    self.handle_chain_message(message, conn, neighbour_id, message_type)

                elif message_type == Messages.MESSAGE_TYPE_PING.value:
                    self.handle_general_message(message, conn, neighbour_id)

            except json.JSONDecodeError as e:
                logging.error("Error decoding JSON:", e)
                logging.info(f"Retrying attempts left {self.retries}...")
                self.retries -= 1
                time.sleep(1)
                if self.retries <= 0:
                    break

            except ssl.SSLZeroReturnError as e:
                logging.error(f"SSLZero Return Error {e.strerror}")
                break

            except socket.timeout as e:
                logging.error("Error timeout:", e.args)
                self.recon_state = True
                if conn in self.connections:
                    self.remove_node(conn, "Timeout")
                    conn.close()
                    handle_reconects = threading.Thread(target=self.handle_reconnects)
                    handle_reconects.start()
                    break

            except ConnectionResetError as c:
                logging.error(f"Connection Reset Error {c.strerror}")
                if conn in self.connections:
                    self.remove_node(conn, "ConnectionResetError")
                    conn.close()
                break

            except OSError as e:
                logging.error(f"System Error {e.strerror}")
                if conn in self.connections:
                    self.remove_node(conn, "OSError")
                    conn.close()
                break

            except Exception as ex:
                logging.error(f"Exception Error {ex.args}")
                if conn in self.connections:
                    self.remove_node(conn, "Exception")
                    conn.close()
                break

    def create_blockchain_transaction(self, event_action, event_type, event_local, event_description="",
                                      event_accuracy="1.0"):
        """
        Creates and returns a new blockchain transaction with the specified event information.

        This method generates a new transaction containing event details such as event action, event type,
        and event local information. It then signs the transaction with the node's private key and returns
        the transaction along with its corresponding signature.

        :param event_description:
        :param event_accuracy:
        :param event_action: The action associated with the event.
        :param event_type: The type of the event.
        :param event_local: The local context of the event.

        :return: A dictionary containing the signed transaction and its signature, or None if the transaction
                 is already in the pending transactions pool.
        """
        message_tx = {
            "EVENT_TYPE": event_type,
            "EVENT_ACTION": event_action,
            "EVENT_LOCAL": event_local,
            "EVENT_DESCRIPTION": event_description,
            "EVENT_ACCURACY": event_accuracy,
        }

        tx, signature = create_transaction(
            self.private_key, self.public_key, str(self.id),
            message_tx["EVENT_ACTION"], message_tx["EVENT_TYPE"],
            message_tx["EVENT_LOCAL"],
            message_tx["EVENT_ACCURACY"],
            message_tx["EVENT_DESCRIPTION"],
        )

        transaction_with_signature = {
            "DATA": tx,
            "SIGNATURE": signature,
        }

        if transaction_with_signature not in self.blockchain.pending_transactions:
            self.blockchain.pending_transactions.append(transaction_with_signature)
            return transaction_with_signature

        return None

    def broadcast_message(self, message):
        """
        The ``broadcast_message`` method broadcasts a message to all connected peers. The message is encoded and sent to
        each peer using the ``sendall`` method of the socket object.

        :param message: The message to be broadcast
        :type message: <bytes>
        :return: None
        """
        for peer in self.connections:
            peer.sendall(bytes(message, encoding="utf-8"))

    def list_peers(self):
        """Prints a list of all connected peers.

        Prints the IP address and port number of each connected peer, using the format:
        [<index>] <IP address>:<port number>

        :return: None
        """
        print("\nPeers:")
        for i, conn in enumerate(self.connections):
            print(f"[{i}] <{conn.getpeername()[0]}:{conn.getpeername()[1]}>")

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
