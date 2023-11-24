# This code was adapted from the original code by Daniel van Flymen
# Source: https://github.com/dvf/blockchain-book
# Source: https://github.com/valvesss/blopy/blob/master/blopy/blockchain.py
import json
import logging
import math
import time
import random
from asyncio.log import logger
from hashlib import sha256
from EdgeDevice.utils.helper import Utils
import ntplib
from time import ctime


class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.pending_transactions = []
        self.target = "0000ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        self.nodes = {}
        self.running = True
        self.sync_clocks()

    def get_synchronized_time(self):
        """
        Retorna o tempo sincronizado levando em consideração o offset do tempo local.
        """
        return time.time() + self.local_time_offset

    def sync_clocks(self):
        # Sincronizar o relógio com um servidor NTP
        client = ntplib.NTPClient()
        response = client.request('pool.ntp.org')
        self.local_time_offset = response.offset

    def register_node(self, connection_peer):
        """
        Add a new node to the list of nodes
        :param connection_peer: Address of node, e.g. '192.168.X.X'.
        """
        self.nodes.update(connection_peer)

    def new_block(self):
        """
        This method generates a new block for the blockchain. It follows a set of steps to construct the block with
        the necessary attributes. The process starts by determining the height of the block, which is equal to the
        length of the current chain. The transactions included in the block are taken from the pending transactions
        list. The previous hash of the last block in the chain is used as a reference for linking the new block. The
        nonce, a randomly generated hexadecimal value, is assigned to the block to satisfy the target difficulty. The
        target difficulty represents the level of computational effort required to find a valid nonce.

        The timestamp is set to the current time when the block is created. Once the block is constructed,
        it undergoes validation to ensure it meets the target difficulty and satisfies the blockchain's rules. If the
        block passes the validation process, the list of pending transactions is reset, and the new block is returned.

        This method operates within a loop, indicating that it is continuously generating new blocks as long as the
        system is running. It is essential for maintaining the growth and integrity of the blockchain by consistently
        adding valid blocks with confirmed transactions.
        :return block: Block created with the validated parameters
        """
        while self.running:
            block = self.create_block(
                height=len(self.chain),
                transactions=self.pending_transactions,
                previous_hash=self.last_block["HASH"] if self.last_block else None,
                nonce=format(random.getrandbits(64), "x"),
                target=self.target,
                timestamp=self.get_synchronized_time(),
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
        """
        The create_block method is a static method of a blockchain class responsible for generating a new block with
        the provided attributes. Here is a scientific description of the method:

        This static method constructs a new block for the blockchain. It takes several attributes as input,
        including the height of the block, the list of transactions to include, the hash of the previous block,
        a nonce value, a target difficulty, and an optional timestamp.

        The method creates a block dictionary and assigns the provided attributes to their corresponding keys in the
        dictionary. The height represents the position of the block in the blockchain. The transactions list contains
        the transactions to be included in the block. The previous hash is the cryptographic hash of the previous
        block in the chain, ensuring the immutability and integrity of the blockchain. The nonce is a randomly
        generated value used in the mining process to find a valid block. The target difficulty indicates the level
        of difficulty required to find a valid nonce.

        If a timestamp is not provided, the current time is used as the timestamp for the block. Once the block
        attributes are set, the method calculates the hash of the block. It converts the block dictionary into a JSON
        string, sorts the keys for consistency, encodes the string, and applies the SHA-256 hash function to generate
        a unique block hash. The block hash is then added to the block dictionary.

        Finally, the method returns the constructed block with all the assigned attributes, including the calculated
        hash.

        The create_block method serves as a utility function for creating individual blocks in the blockchain. It is
        used internally within the blockchain class to generate valid blocks with the necessary attributes and their
        corresponding hashes.

        :param height: The height of the block in the blockchain.
        :type height: <int>
        :param transactions: The list of transactions to include in the block.
        :type transactions: <list>
        :param previous_hash: The hash of the previous block in the blockchain.
        :type previous_hash: <str>
        :param nonce: The nonce value for mining the block.
        :type nonce: <str>
        :param target: The target difficulty for finding a valid block.
        :type target: <int>
        :param timestamp: The timestamp of the block (optional). If not provided, the current time will be used.
        :type timestamp: <float> or None
        :return: The newly created block with all its attributes.
        :rtype: <dict>
        """
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
        """
        This static method takes a block as input and calculates its hash value. The block is a dictionary
        representing a block in the blockchain. The method ensures that the dictionary keys are sorted to maintain
        consistency in the hash calculation. It converts the block dictionary into a JSON string, sorts the keys,
        encodes the string, and applies the SHA-256 hash function. The resulting hash value is returned as a
        hexadecimal string.
        :param block: Dictionary representing a block in the blockchain.
        :type block: <dict>
        :return: Hexadecimal string representing the block's hash value.
        """
        # We ensure the dictionary is sorted or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return sha256(block_string).hexdigest()

    @property
    def last_block(self):
        """
        This method is a property that returns the last block in the blockchain. It checks if there are blocks in the
        chain and returns the last block if it exists. If the chain is empty, it returns None. The method provides
        convenient access to the most recent block in the chain.
        :return: Returns the last block in the chain (if there are blocks)
        """
        return self.chain[-1] if self.chain else None

    def valid_block(self, block):
        """
        This method checks if a given block meets the target difficulty of the blockchain. It compares the hash value
        of the block (block["HASH"]) with the target difficulty (self.target). If the block's hash value is less than
        the target, indicating that the block meets the required difficulty level, the method returns True.
        Otherwise, it returns False.
        :param block: A dictionary representing a block in the blockchain.
        :type block: <dict>
        :return: Returns false if the hash value of the block is greater than or equal to the target difficulty else
        returns true.
        """
        return block["HASH"] < self.target

    def validate(self, block):
        """
        This method performs additional validation checks on a block. If the height of the block is 0 (indicating the
        genesis block), the method immediately returns True to bypass further validation. Otherwise, it calls the
        Validate function, passing the block as an argument. The Validate function is assumed to be defined
        elsewhere. If the Validate function returns a non-empty dictionary with valid key-value pairs and a valid
        proof, the method updates the block's hash with the calculated block hash (validate.block_hash) and returns
        True. Otherwise, it returns False.
        :param block: A dictionary representing a block in the blockchain.
        :type block: <dict>
        :return: Returns true if the validation conditions are met, indicating that the block is considered valid.
        """
        if block['HEIGHT'] == 0:
            return True

        validate = self.Validate(block)
        if validate.keys() and validate.values() and validate.proof():
            block['HASH'] = validate.block_hash
            return True
        return False

    def add_block(self, block):
        """
        This method is responsible for adding a block to the blockchain. It appends the provided block to the
        self.chain list. The method allows adding blocks to the blockchain without performing comprehensive
        validation. It serves as a placeholder for implementing appropriate validation logic in the future.
        :param block: A dictionary representing a block in the blockchain.
        :type block: <dict>
        :return: None
        """
        self.chain.append(block)

    def recalculate_target(self, block_index):
        """
        The recalculate_target method is responsible for recalculating the target difficulty for mining blocks in the
        blockchain. Here is a scientific description of the method:

        This method determines whether the target difficulty needs to be recalculated based on the given block index.
        If the block index is divisible by 10 without a remainder, the target difficulty recalculation is triggered.

        The method begins by defining the expected time span for mining 10 blocks, which is set to 10 times a
        predefined constant value (e.g., 10 seconds per block). It then calculates the actual time span between the
        most recent block ( self.chain[-1]) and the block that occurred 10 blocks ago (self.chain[-10]).

        To determine the offset or adjustment factor, the ratio between the expected timespan and the actual timespan
        is calculated. This ratio represents the difference between the expected and actual mining rates. If the
        actual timespan is shorter than the expected timespan, the ratio will be greater than 1, indicating that the
        mining rate is faster than expected. Conversely, if the actual timespan is longer, the ratio will be less
        than 1, indicating a slower mining rate.

        Next, the method calculates the new target difficulty by multiplying the current target difficulty (
        represented as an integer value) by the ratio. The resulting value is then converted back to a hexadecimal
        representation and stored as the new target difficulty (self.target).

        For debugging purposes, the method prints the new target difficulty. Finally, the recalculated target
        difficulty is returned.

        The recalculate_target method ensures that the blockchain's target difficulty adjusts dynamically based on
        the mining rate of the previous blocks. By recalculating the target difficulty periodically, the blockchain
        can maintain a consistent block mining rate and adapt to changes in network computing power.

        :param block_index: Represents height of block
        :type block_index: <int>
        :return: Return the recalculated target difficulty

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
        """
        The get_blocks_after_timestamp method is a member method of a blockchain class. It retrieves all blocks in
        the blockchain that have timestamps greater than a specified timestamp. Here is a scientific description of
        the method:

        This method iterates over each block in the blockchain, starting from the first block. It compares the
        timestamp of each block with the provided timestamp. If the block's timestamp is greater than the provided
        timestamp, it means that the block was added to the blockchain after the specified time. In that case,
        the method returns a new list containing all the blocks from the current block onwards until the end of the
        blockchain.

        The method allows for querying the blockchain for blocks that were added after a certain point in time. It
        provides a way to retrieve blocks that are relevant to specific time periods or events in the blockchain's
        history.


        :param timestamp: Speciffied timestamp
        :type timestamp: <float>
        :return:
        """
        for index, block in enumerate(self.chain):
            if timestamp < block["TIMESTAMP"]:
                return self.chain[index:]

    def mine_new_block(self):
        """
        The mine_new_block method is a member method of a blockchain class. It is responsible for mining a new block
        and adding it to the blockchain. Here is a scientific description of the method:

        First, the method recalculates the target difficulty for the next block based on the height of the last block
        in the blockchain plus one.

        Next, the method enters a loop, repeatedly attempting to mine a new block. Inside the loop, it calls the
        new_block method to generate a new block candidate. It then checks if the candidate block is valid by calling
        the valid_block method. If the candidate block is valid, meaning it meets the target difficulty requirements
        and passes other validation checks, the loop breaks, and the mining process is successful. If the candidate
        block is not valid, the method varies the nonce value in the block and repeats the mining process. The nonce
        is a randomly generated value used in the mining process to find a valid block hash. By changing the nonce
        and reattempting the mining process, the method explores different possibilities to find a suitable hash that
        satisfies the target difficulty. Once a valid block is mined, it is added to the blockchain by calling the
        add_block method. Finally, the method logs a message indicating that a new block has been found.

        The mine_new_block method plays a crucial role in the blockchain's consensus mechanism by continuously
        attempting to find valid blocks. It demonstrates the process of mining and adding new blocks to the
        blockchain, ensuring the integrity and security of the blockchain network.

        :return: None
        """

        self.sync_clocks()
        self.recalculate_target(self.last_block["HEIGHT"] + 1)
        while self.running:
            new_block = self.new_block()
            if self.valid_block(new_block):
                break

            # Vary the nonce to find a suitable hash
            new_block["NONCE"] = format(random.getrandbits(64), "x")

        self.add_block(new_block)
        logger.info("Found a new block:", new_block)

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
            """
            The constructor method of the Validate class initializes an instance with the provided block dictionary.
            It also initializes the block_hash attribute by calling the block_hash() method and removes the HASH key
            from the block dictionary.

            :param block: A dictionary representing a block in the blockchain.
            :type block: <dict>
            """
            self.block = block
            self.block_hash = self.block_hash()
            self.remove_hash()

        def remove_hash(self):
            """
            This method checks if the HASH key exists in the block dictionary. If it does, it assigns the value of
            the HASH key to the block_hash attribute and removes the HASH key from the block dictionary.
            :return: None
            """
            if 'HASH' in self.block:
                self.block_hash = self.block['HASH']
                del self.block['HASH']

        def block_hash(self):
            """
            This method retrieves the value of the HASH key from the block dictionary, if it exists.
            :return: Returns the block hash value
            """
            if 'HASH' in self.block:
                print(self.block['HASH'])
                return self.block['HASH']

        def keys(self):
            """
            The keys() method validates whether the block dictionary contains all the required keys specified in the
            block_required_items dictionary. It utilizes the validate_dict_keys method from the utils instance to
            perform the validation.

            :return: If all the required keys are present, it returns True; otherwise, it returns False.
            """
            if self.utils.validate_dict_keys(self.block, self.block_required_items):
                return True
            return False

        def values(self):
            """
            The values() method validates whether the values of the keys in the block dictionary match the expected
            types specified in the block_required_items dictionary. It uses the validate_dict_values method from the
            utils instance to perform the validation.
            :return: If all the values match the expected types, it returns True; otherwise, it returns False.
            """

            if self.utils.validate_dict_values(self.block, self.block_required_items):
                return True
            return False

        def proof(self):
            """
            The proof() method checks the validity of the block's proof of work. It computes the hash of the block
            dictionary using the compute_hash method from the utils instance. It then compares the computed hash with
            the block_hash attribute to ensure consistency. Additionally, it checks if the computed hash starts with
            a certain number of leading zeros (indicating a valid proof).
            :return: If the proof is valid, it returns True; otherwise, it logs an error message and returns False.
            """

            block_hash = self.utils.compute_hash(self.block)
            if (not (block_hash.startswith('0' * 2) or
                     block_hash != self.block_hash)):
                logging.error('Server Blockchain: Block #{} has no valid proof!'.format(self.block['HEIGHT']))
                return False
            return True
