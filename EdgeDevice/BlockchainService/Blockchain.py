# This code was adapted from the original code by Daniel van Flymen
# Source: https://github.com/dvf/blockchain-book
# Source: https://github.com/valvesss/blopy/blob/master/blopy/blockchain.py
import asyncio
import hashlib
import json
import math
import time
import random
from asyncio.log import logger
from hashlib import sha256


class Blockchain:
    def __init__(self):
        self.pending_transactions = []
        self.target = "0000ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        self.chain = []
        self.nodes = {}
        self.chain.append(self.new_block())

    def new_block(self):
        block = self.create_block(
            height=len(self.chain),
            transactions=self.pending_transactions,
            previous_hash=self.last_block["hash"] if self.last_block else None,
            nonce=format(random.getrandbits(64), "x"),
            target=self.target,
            timestamp=time.time(),
        )

        # Reset the list of pending transactions
        self.pending_transactions = []

        return block

    @staticmethod
    def create_block(
            height, transactions, previous_hash, nonce, target, timestamp=None
    ):
        block = {
            "height": height,
            "transactions": transactions,
            "previous_hash": previous_hash,
            "nonce": nonce,
            "target": target,
            "timestamp": timestamp or time.time(),
        }

        # Get the hash of this new block, and add it to the block
        block_string = json.dumps(block, sort_keys=True).encode()
        block["hash"] = sha256(block_string).hexdigest()
        return block

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
        if len(self.chain) > 0:
            for block in self.chain:
                blocks.append({'height': block.height, 'timestamp': block.timestamp,
                               'data': block.data, 'previous_hash': block.previous_hash, 'hash': block.hash})
        return json.dumps(blocks, sort_keys=True)

    def from_json(self, json_chain):
        self.chain = []
        for block_json in json.loads(json_chain):
            block = {
                'height': block_json['height'],
                'timestamp': block_json['timestamp'],
                'transactions': block_json['data'],
                'nonce': block_json['nonce'],
                'previous_hash': block_json['previous_hash'],
            }
            self.chain.append(block)

        # Reset the current list of transactions
        self.pending_transactions = []
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
            'transactions': self.pending_transactions,
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
        self.pending_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1

    @property
    def last_block(self):
        # Returns the last block in the chain (if there are blocks)
        return self.chain[-1] if self.chain else None

    def valid_block(self, block):
        # Check if a block's hash is less than the target...
        return block["hash"] < self.target

    def add_block(self, block):
        # TODO: Add proper validation logic here!
        self.chain.append(block)

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

    def recalculate_target(self, block_index):
        """
        Returns the number we need to get below to mine a block
        """
        # Check if we need to recalculate the target
        if block_index % 10 == 0:
            # Expected time span of 10 blocks
            expected_timespan = 10 * 10

            # Calculate the actual time span
            actual_timespan = self.chain[-1]["timestamp"] - self.chain[-10]["timestamp"]

            # Figure out what the offset is
            ratio = actual_timespan / expected_timespan

            # Now let's adjust the ratio to not be too extreme
            ratio = max(0.25, ratio)
            ratio = min(4.00, ratio)

            # Calculate the new target by multiplying the current one by the ratio
            new_target = int(self.target, 16) * ratio

            self.target = format(math.floor(new_target), "x").zfill(64)
            logger.info(f"Calculated new mining target: {self.target}")

        return self.target

    def get_blocks_after_timestamp(self, timestamp):
        for index, block in enumerate(self.chain):
            if timestamp < block["timestamp"]:
                return self.chain[index:]

    def mine_new_block(self):
        self.recalculate_target(self.last_block["index"] + 1)
        while True:
            new_block = self.new_block()
            if self.valid_block(new_block):
                break

            time.sleep(1)

        self.chain.append(new_block)
        logger.info("Found a new block: ", new_block)
