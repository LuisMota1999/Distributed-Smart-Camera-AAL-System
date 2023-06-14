# This code was adapted from the original code by Daniel van Flymen
# Source: https://github.com/dvf/blockchain-book
# Source: https://github.com/valvesss/blopy/blob/master/blopy/blockchain.py
import hashlib
import json
import logging
import math
import time
import random
from asyncio.log import logger
from hashlib import sha256
from EdgeDevice.utils.helper import Utils


class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.pending_transactions = []
        self.target = "0000ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        self.nodes = {}
        self.running = True
        # Create the genesis block
        logger.info("Creating genesis block")

    def register_node(self, connection_peer):
        """
        Add a new node to the list of nodes
        :param connection_peer: Address of node, e.g. '192.168.X.X'.
        """
        self.nodes.update(connection_peer)

    def new_block(self):
        while self.running:
            block = self.create_block(
                height=len(self.chain),
                transactions=self.pending_transactions,
                previous_hash=self.last_block["HASH"] if self.last_block else None,
                nonce=format(random.getrandbits(64), "x"),
                target=self.target,
                timestamp=time.time(),
            )

            # Check if the block meets the target difficulty
            if self.valid_block(block):
                # Reset the list of pending transactions
                self.pending_transactions = []
                if self.validate(block):
                    return block

    @staticmethod
    def create_block(
            height, transactions, previous_hash, nonce, target, timestamp=None
    ):
        block = {
            "HEIGHT": height,
            "TRANSACTIONS": transactions,
            "PREVIOUS_HASH": previous_hash,
            "NONCE": nonce,
            "TARGET": target,
            "TIMESTAMP": timestamp or time.time(),
        }

        # Get the hash of this new block, and add it to the block
        block_string = json.dumps(block, sort_keys=True).encode()
        block["HASH"] = sha256(block_string).hexdigest()

        return block

    @staticmethod
    def hash(block):
        # We ensure the dictionary is sorted or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return sha256(block_string).hexdigest()

    @property
    def last_block(self):
        # Returns the last block in the chain (if there are blocks)
        return self.chain[-1] if self.chain else None

    def valid_block(self, block):
        # Check if a block's hash is less than the target...
        return block["HASH"] < self.target

    def validate(self, block):
        if block['HEIGHT'] == 0:
            return True

        validate = self.Validate(block)
        if validate.keys() and validate.values() and validate.proof():
            block['HASH'] = validate.block_hash
            return True
        return False

    def add_block(self, block):
        # TODO: Add proper validation logic here!
        self.chain.append(block)

    def recalculate_target(self, block_index):
        """
        Returns the number we need to get below to mine a block
        """
        # Check if we need to recalculate the target
        if block_index % 10 == 0:
            # Expected time span of 10 blocks
            expected_timespan = 10 * 10

            # Calculate the actual time span
            actual_timespan = self.chain[-1]["TIMESTAMP"] - self.chain[-10]["TIMESTAMP"]

            # Figure out what the offset is
            ratio = expected_timespan / actual_timespan

            # Calculate the new target by multiplying the current one by the ratio
            new_target = int(self.target, 16) * ratio

            # Convert the new target back to hexadecimal representation
            new_target_hex = format(math.floor(new_target), "x").zfill(64)

            # Update the target difficulty
            self.target = new_target_hex

            # Print the new target difficulty for debugging
            print("New Target Difficulty:", self.target)

        return self.target

    def get_blocks_after_timestamp(self, timestamp):
        for index, block in enumerate(self.chain):
            if timestamp < block["TIMESTAMP"]:
                return self.chain[index:]

    def mine_new_block(self):
        self.recalculate_target(self.last_block["HEIGHT"] + 1)
        while self.running:
            new_block = self.new_block()
            if self.valid_block(new_block):
                break

            # Vary the nonce to find a suitable hash
            new_block["NONCE"] = format(random.getrandbits(64), "x")

        self.add_block(new_block)
        # logger.info("Found a new block:", new_block)

    class Validate(object):
        utils = Utils()
        block_required_items = {'HEIGHT': int,
                                'TRANSACTIONS': list or None,
                                'PREVIOUS_HASH': str,
                                'NONCE': str,
                                'TARGET': str,
                                'TIMESTAMP': float
                                }

        def __init__(self, block):
            self.block = block
            self.block_hash = self.block_hash()
            self.remove_hash()

        def remove_hash(self):
            if 'HASH' in self.block:
                self.block_hash = self.block['HASH']
                del self.block['HASH']

        def block_hash(self):
            if 'HASH' in self.block:
                print(self.block['HASH'])
                return self.block['HASH']

        def keys(self):
            if self.utils.validate_dict_keys(self.block, self.block_required_items):
                return True
            return False

        def values(self):
            if self.utils.validate_dict_values(self.block, self.block_required_items):
                return True
            return False

        def proof(self):
            block_hash = self.utils.compute_hash(self.block)
            if (not (block_hash.startswith('0' * 2) or
                     block_hash != self.block_hash)):
                logging.error('Server Blockchain: Block #{} has no valid proof!'.format(self.block['HEIGHT']))
                return False
            return True
