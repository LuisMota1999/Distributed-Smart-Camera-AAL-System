import hashlib
import json
import time
import requests
from flask import jsonify
from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf, ServiceStateChange, IPVersion
import threading
import socket
import argparse
import logging
from typing import cast
import netifaces as ni
import random


class Blockchain:
    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()

        # Create the genesis block
        self.new_block(previous_hash='1', proof=100)

    def register_node(self, address):
        """
        Add a new node to the list of nodes
        :param address: Address of node. Eg. 'http://192.168.0.5:5000'
        """
        self.nodes.add(address)

    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid
        :param chain: A blockchain
        :return: True if valid, False if not
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        This is our consensus algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        :return: True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_block(self, proof, previous_hash):
        """
        Create a new Block in the Blockchain
        :param proof: The proof given by the Proof of Work algorithm
        :param previous_hash: Hash of previous Block
        :return: New Block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time.time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined Block
        :param sender: Address of the Sender
        :param recipient: Address of the Recipient
        :param amount: Amount
        :return: The index of the Block that will hold this transaction
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block
        :param block: Block
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_proof):
        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
         - p is the previous proof, and p' is the new proof
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Validates the Proof
        :param last_proof: Previous Proof
        :param proof: Current Proof
        :return: True if correct, False if not.
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"


HOST_NAME = socket.gethostname()
SERVICE_TYPE = "_node._tcp.local."
HOST_PORT = random.randint(5000, 6000)


class NodeListener:
    def __init__(self, node):
        self.node = node

    def remove_service(self, zeroconf, service_type, name):
        info = zeroconf.get_service_info(service_type, name)
        if info:
            ip_address = info.properties[b'IP']
            ip_address = ip_address.decode('UTF-8')
            self.node.remove_node(ip_address)

    def add_service(self, zeroconf, service_type, name):
        info = zeroconf.get_service_info(service_type, name)
        if info:
            ip_list = info.parsed_addresses()
            for ip in ip_list:
                self.node.add_node(ip, info.port)
                if ip != ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']:
                    self.node.connect_to_peer(ip, info.port)

    def update_service(self,
                       zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange
                       ) -> None:
        print(f"Service {name} of type {service_type} state changed: {state_change}")

        if state_change is ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            # print("Info from zeroconf.get_service_info: %r" % (info))

            if info:
                addresses = ["%s:%d" % (addr, cast(int, info.port)) for addr in info.parsed_scoped_addresses()]
                print("  Addresses: %s" % ", ".join(addresses))
                print("  Weight: %d, priority: %d" % (info.weight, info.priority))
                print("  Port: %d" % info.port)

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
        self.last_keep_alive = 30  # time.time()
        self.discovered_nodes = set()
        self.zeroconf = Zeroconf()
        self.listener = NodeListener(self)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', self.port))
        self.socket.listen(10)
        self.running = True
        self.connections = []
        self.blockchain = Blockchain()

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
        if args.v6:
            ip_versionX = IPVersion.All
        elif args.v6_only:
            ip_versionX = IPVersion.V6Only
        else:
            ip_versionX = IPVersion.V4Only

        hostname = socket.gethostname()

        print(f"HOSTNAME - {hostname}")
        service_info = ServiceInfo(
            type_="_node._tcp.local.",
            name=f"{self.name}._node._tcp.local.",
            addresses=[socket.inet_aton(self.ip)],
            port=HOST_PORT,
            weight=0,
            priority=0,
            properties={'IP': self.ip},
        )

        zc = Zeroconf(ip_version=ip_versionX)
        zc.register_service(service_info)

    def run(self):
        # Start the service browser
        browser = ServiceBrowser(self.zeroconf, "_node._tcp.local.", [self.listener.update_service])
        threading.Thread(target=self.accept_connections).start()

    def accept_connections(self):
        while self.running:
            conn, addr = self.socket.accept()
            print(f"Connected to {addr[0]}:{addr[1]}")

            # Start a thread to handle incoming messages
            threading.Thread(target=self.handle_messages, args=(conn,)).start()

    def connect_to_peer(self, client_host, client_port):
        while True:
            try:
                conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                conn.connect((client_host, client_port))
                self.connections.append(conn)
                self.broadcast_message(f"[Connected]: [{client_host}]")
                break
            except ConnectionRefusedError:
                print(f"Connection refused by {client_host}:{client_port}, retrying in 10 seconds...")
                time.sleep(10)

        # Start a thread to handle incoming messages
        threading.Thread(target=self.handle_messages, args=(conn,)).start()
        threading.Thread(target=self.send_keep_alive_messages, args=(conn,)).start()

    def send_keep_alive_messages(self, conn):

        while True:
            try:
                # send a keep-alive message every 60 seconds
                # assume 'sock' is the socket object
                laddress = conn.getsockname()
                raddress = conn.getpeername()
                conn.send(f'[KA] - From [{laddress[0]}]:[{laddress[1]}] TO [{raddress[0]}]:[{raddress[1]}]'.encode())
                time.sleep(self.last_keep_alive)
            except:
                # handle socket errors here
                self.stop()
                break

    def broadcast_message(self, message):
        for peer in self.connections:
            peer.sendall(message.encode())

    def handle_messages(self, conn):
        while True:
            message = conn.recv(1024).decode()
            if not message:
                break
            print(f"Received message: {message}")

    def new_transaction(self, sender, recipient, amount):
        # Create a new Transaction
        index = self.blockchain.new_transaction(sender, recipient, amount)

        response = {'message': f'Transaction will be added to Block {index}'}
        return jsonify(response), 201

    def full_chain(self):
        response = {
            'chain': self.blockchain.chain,
            'length': len(self.blockchain.chain),
        }
        return jsonify(response), 200

    def mine(self, node_identifier):
        # We run the proof of work algorithm to get the next proof...
        last_block = self.blockchain.last_block
        last_proof = last_block['proof']
        proof = self.blockchain.proof_of_work(last_proof)

        # We must receive a reward for finding the proof.
        # The sender is "0" to signify that this node has mined a new coin.
        self.blockchain.new_transaction(
            sender="0",
            recipient=node_identifier,
            amount=1,
        )

        # Forge the new Block by adding it to the chain
        previous_hash = self.blockchain.hash(last_block)
        block = self.blockchain.new_block(proof, previous_hash)

        response = {
            'message': "New Block Forged",
            'index': block['index'],
            'transactions': block['transactions'],
            'proof': block['proof'],
            'previous_hash': block['previous_hash'],
        }
        return jsonify(response), 200

    def consensus(self):
        replaced = self.blockchain.resolve_conflicts()

        if replaced:
            response = {
                'message': 'Our chain was replaced',
                'new_chain': self.blockchain.chain
            }
        else:
            response = {
                'message': 'Our chain is authoritative',
                'chain': self.blockchain.chain
            }

        return jsonify(response), 200

    def list_peers(self):
        print("Peers [IP:PORT]:")
        for peer in self.discovered_nodes:
            print(peer)
        print("Connections:")
        for conn in self.connections:
            print(conn)

    def stop(self):
        self.running = False
        self.zeroconf.close()

    def add_node(self, client_ip, client_port):
        if client_ip not in self.discovered_nodes:
            self.discovered_nodes.add((client_ip, client_port))
            self.blockchain.register_node((client_ip, client_port))
            print(f"Node {client_ip} added to the network")
            print(f"Discovered nodes: {self.discovered_nodes}")
            print(f"Nodes in Blockchain: {list(self.blockchain.nodes)}")

    def remove_node(self, ip):
        if ip in self.discovered_nodes:
            self.discovered_nodes.remove(ip)
            print(f"Node {ip} removed from the network")
            print(f"Nodes still available: {self.discovered_nodes}")


def main():
    node = Node(HOST_NAME)
    print(f"Listening on {node.ip}:{node.port}...")
    node.start()
    time.sleep(2)
    node_thread = threading.Thread(target=node.starter)
    node_thread.start()


if __name__ == "__main__":
    main()

# https://gist.github.com/victorazzam/b34e9fb3d4b1e84e9c1841635071201d
