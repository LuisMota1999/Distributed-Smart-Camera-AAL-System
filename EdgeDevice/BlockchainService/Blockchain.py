# This code was adapted from the original code by Daniel van Flymen
# Source: https://github.com/dvf/blockchain-book

import hashlib
import json
import time
import requests


class Blockchain:
    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = {}
        self.create_genesis_block()

    def create_genesis_block(self):
        return self.add_block(previous_hash='1', proof=100)

    def register_node(self, connection_peer):
        """
        Add a new node to the list of nodes
        :param connection_peer: Address of node, e.g. '192.168.X.X'.
        """
        self.nodes.update(connection_peer)

    def get_latest_block(self):
        return self.chain[-1]

    def to_json(self):
        blocks = []
        print(self.chain)
        if len(self.chain) > 0:
            for block in self.chain:
                blocks.append({'index': block.index, 'timestamp': block.timestamp,
                               'data': block.data, 'previous_hash': block.previous_hash, 'hash': block.hash})

        for keys, value in blocks.items():
            print(f"{keys}:{value}\n")

        return json.dumps(blocks, sort_keys=True)

    def from_json(self, json_chain):
        self.chain = []
        for block_json in json.loads(json_chain):
            block = {
                'index': block_json['index'],
                'timestamp': block_json['timestamp'],
                'transactions': block_json['data'],
                'proof': 100,
                'previous_hash': block_json['previous_hash'],
            }
            self.chain.append(block)

        # Reset the current list of transactions
        self.current_transactions = []
        return self

    def valid_chain(self, chain):
        """
        Determine if a given BlockchainService is valid
        :param chain: A BlockchainService
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

    def add_block(self, proof, previous_hash):
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
