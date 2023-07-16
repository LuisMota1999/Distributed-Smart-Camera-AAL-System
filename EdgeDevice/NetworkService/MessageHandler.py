import json
import logging
import time
import uuid

from EdgeDevice.BlockchainService.Transaction import validate_transaction
from EdgeDevice.utils.constants import Messages

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

