import random
import json
import logging
import ssl
import socket
import time
import uuid

from EdgeDevice.BlockchainService.Transaction import validate_transaction
from EdgeDevice.utils.constants import Messages, BUFFER_SIZE

from EdgeDevice.utils.helper import load_public_key_from_json, public_key_to_json, create_general_message


class MessageHandler:
    def __init__(self, node):
        self.node = node

    def handle_keep_alive_messages(self, conn, client_id):
        """
        The ``handle_keep_alive_messages`` method sends keep-alive messages to the specified connection periodically
        to maintain the connection. The keep-alive message
        includes information such as the sender's metadata, message type, last time alive, coordinator information, and
        public key. If an exception occurs during the process, the function breaks the loop and closes the connection.

        :param conn: Socket connection object representing the connection to the peer node.
        :type conn: <socket.socket>
        :param client_id: The unique identifier of the connected peer node.
        :type client_id: <bytes>
        :return: None
        """
        neighbour_id = uuid.UUID(client_id.decode('utf-8'))
        neighbour = self.node.neighbours.get(neighbour_id)
        while self.node.running:
            try:
                data = create_general_message(str(self.node.id), self.node.ip, self.node.port, conn.getpeername()[0],
                                              conn.getpeername()[1],
                                              str(neighbour_id), str(self.node.coordinator),
                                              Messages.MESSAGE_TYPE_PING.value)

                if neighbour is not None and neighbour['PUBLIC_KEY'] is None:
                    data["PAYLOAD"]["PUBLIC_KEY"] = public_key_to_json(self.node.public_key)

                time.sleep(2)
                message = json.dumps(data, indent=2)
                conn.send(bytes(message, encoding="utf-8"))
                time.sleep(self.node.keep_alive_timeout)
            except Exception as ex:  # Catch the specific exception you want to handle
                logging.error(f"Exception error in Keep Alive: {ex.args}")
                break

        if conn in self.node.connections:
            self.node.recon_state = True
            self.node.remove_node(conn, "KAlive")
            client_id_str = client_id.decode('utf-8')
            client_uuid = uuid.UUID(client_id_str)
            if client_uuid in self.node.neighbours:
                self.node.neighbours.pop(client_uuid)
            conn.close()

    def handle_chain_message(self, message, conn, neighbour_id, message_type):
        if message_type == Messages.MESSAGE_TYPE_GET_CHAIN.value:
            if self.node.coordinator == uuid.UUID(message["PAYLOAD"].get("COORDINATOR")):
                data = create_general_message(str(self.node.id), self.node.ip, self.node.port, conn.getpeername()[0],
                                              conn.getpeername()[1],
                                              str(neighbour_id), str(self.node.coordinator),
                                              Messages.MESSAGE_TYPE_CHAIN_RESPONSE.value)

                data["PAYLOAD"]["CHAIN"] = self.node.blockchain.chain

                message_json = json.dumps(data, indent=2)
                logging.info(f"CHAIN MESSAGE: {message_json}")
                conn.send(bytes(message_json, encoding="utf-8"))
        elif message_type == Messages.MESSAGE_TYPE_CHAIN_RESPONSE.value:
            self.node.blockchain.chain = message["PAYLOAD"].get("CHAIN")
            logging.info(f"IP: {self.node.ip} , CHAIN: {self.node.blockchain.chain}")
            logging.info("Blockchain chain was updated with information from coordinator")

    def handle_transaction_message(self, message, conn, neighbour_id):
        tx = message["PAYLOAD"]["PENDING"]

        if validate_transaction(tx):
            if tx not in self.node.blockchain.pending_transactions:
                self.node.blockchain.pending_transactions.append(tx)
                data = create_general_message(str(self.node.id), self.node.ip, self.node.port, conn.getpeername()[0],
                                              conn.getpeername()[1],
                                              str(neighbour_id), str(self.node.coordinator),
                                              Messages.MESSAGE_TYPE_TRANSACTION.value)

                data["PAYLOAD"]["PENDING"] = self.node.blockchain.pending_transactions

                message = json.dumps(data, indent=2)
                conn.send(bytes(message, encoding="utf-8"))
        else:
            logging.warning("Received invalid transaction")
            return

    def handle_general_message(self, message, conn, neighbour_id):
        message_type = Messages.MESSAGE_TYPE_PONG.value
        if self.node.coordinator is None:
            self.node.coordinator = uuid.UUID(message["PAYLOAD"].get("COORDINATOR"))
            logging.info(f"Network Coordinator is {self.node.coordinator}")
            message_type = Messages.MESSAGE_TYPE_GET_CHAIN.value

        neighbour = self.node.neighbours.get(neighbour_id)
        if neighbour is not None and neighbour['PUBLIC_KEY'] is None:
            public_key_base64 = message['PAYLOAD']['PUBLIC_KEY']
            public_key = load_public_key_from_json(public_key_base64)
            if public_key is not None:
                self.node.neighbours[neighbour_id]['PUBLIC_KEY'] = public_key

        data = create_general_message(str(self.node.id), self.node.ip, self.node.port, conn.getpeername()[0],
                                      conn.getpeername()[1],
                                      str(neighbour_id), str(self.node.coordinator), message_type)

        if neighbour is not None and neighbour['PUBLIC_KEY'] is None:
            data["PAYLOAD"]["PUBLIC_KEY"] = public_key_to_json(self.node.public_key)

        message_json = json.dumps(data, indent=2)
        # logging.info(f"\nGENERAL MESSAGE: {message_json}\n")
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
        while self.node.running:
            try:
                data = conn.recv(BUFFER_SIZE).decode()
                # logging.info(f"Data found {data}")
                if not data:
                    logging.info(f"Data not found {data}")
                    self.node.service_info.priority = random.randint(1, 100)
                    self.node.zeroconf.update_service(self.node.service_info)
                    break

                message = json.loads(data)
                message_type = message.get("TYPE")
                neighbour_id = uuid.UUID(message['META']['FROM_ADDRESS']['ID'])

                logging.info(f"[MESSAGE TYPE]: {message_type}")

                if message_type == Messages.MESSAGE_TYPE_PING.value:
                    self.handle_general_message(message, conn, neighbour_id)

                elif message_type == Messages.MESSAGE_TYPE_GET_CHAIN.value:
                    self.handle_chain_message(message, conn, neighbour_id, message_type)

                elif message_type == Messages.MESSAGE_TYPE_TRANSACTION.value:
                    self.handle_transaction_message(message, conn, neighbour_id)

                elif message_type == Messages.MESSAGE_TYPE_CHAIN_RESPONSE.value:
                    self.handle_chain_message(message, conn, neighbour_id, message_type)

            except json.JSONDecodeError as e:
                logging.error("Error decoding JSON:", e)
                logging.info(f"Retrying attempts left {self.node.retries}...")
                self.node.retries -= 1
                time.sleep(1)
                if self.node.retries <= 0:
                    break

            except ssl.SSLZeroReturnError as e:
                logging.error(f"SSLZero Return Error {e.strerror}")
                break

            except socket.timeout as e:
                logging.error("Error timeout:", e)
                self.node.recon_state = True
                if conn in self.node.connections:
                    self.node.remove_node(conn, "Timeout")
                    conn.close()
                break

            except ConnectionResetError as c:
                logging.error(f"Connection Reset Error {c.strerror}")
                if conn in self.node.connections:
                    self.node.remove_node(conn, "ConnectionResetError")
                    conn.close()
                break

            except OSError as e:
                logging.error(f"System Error {e.strerror}")
                if conn in self.node.connections:
                    self.node.remove_node(conn, "OSError")
                    conn.close()
                break

            except Exception as ex:
                logging.error(f"Exception Error {ex.args}")
                if conn in self.node.connections:
                    self.node.remove_node(conn, "Exception")
                    conn.close()
                break
