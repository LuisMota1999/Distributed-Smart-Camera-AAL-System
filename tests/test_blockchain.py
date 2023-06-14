import time
import random
from unittest.mock import patch
from nacl.encoding import HexEncoder
from EdgeDevice.BlockchainService.Blockchain import Blockchain
from nacl.signing import SigningKey
from EdgeDevice.BlockchainService.Transaction import create_transaction, validate_transaction


def test_blockchain_register_node():
    bc = Blockchain()
    bc.register_node({'192.168.0.122': time.time()})

    assert bc.nodes == {'192.168.0.122': time.time()}


def test_blockchain_create_genesis_block():
    # Create a sample instance of the Blockchain class
    bc = Blockchain()

    # Set up necessary variables for testing
    height = len(bc.chain)
    transactions = [{'sender': 'A', 'recipient': 'B', 'amount': 1}]
    previous_hash = bc.chain[-1]["HASH"] if bc.chain else None
    nonce = format(random.getrandbits(64), "x")
    target = '0000000FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'

    # Call the create_block function
    block = bc.create_block(height, transactions, previous_hash, nonce, target)

    # Assert the validity of the created block
    assert isinstance(block, dict)  # Ensure block is a dictionary
    assert 'HEIGHT' in block and block['HEIGHT'] == height  # Ensure HEIGHT is set correctly
    assert 'TRANSACTIONS' in block and block['TRANSACTIONS'] == transactions  # Ensure TRANSACTIONS is set correctly
    assert 'PREVIOUS_HASH' in block and block['PREVIOUS_HASH'] == previous_hash  # Ensure PREVIOUS_HASH is set correctly
    assert 'NONCE' in block and block['NONCE'] == nonce  # Ensure NONCE is set correctly
    assert 'TARGET' in block and block['TARGET'] == target  # Ensure TARGET is set correctly
    assert 'TIMESTAMP' in block and isinstance(block['TIMESTAMP'], float)  # Ensure TIMESTAMP is set correctly
    assert 'HASH' in block  # Ensure HASH is set

    # You can also print or log information about the created block for further analysis
    print("\nBlock created:")
    print(block)


def test_mine_mine_block():
    # Create a sample instance of the Blockchain class
    bc = Blockchain()

    # Genesis Block
    bc.add_block(bc.new_block())

    # Set up necessary variables for testing
    bc.target = "0000FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"

    # Mock the behavior of valid_block() to return True
    with patch.object(Blockchain, "valid_block", return_value=True):
        # Mock the behavior of time.sleep() to skip the waiting period
        with patch.object(time, "sleep"):
            # Call the mine_new_block() method
            bc.mine_new_block()

            # Assert that a new block is added to the chain
            assert len(bc.chain) == 2

            # Assert that the block meets the target difficulty
            assert bc.valid_block(bc.chain[0])


def test_create_transaction():
    private_key = SigningKey.generate().encode(encoder=HexEncoder).decode("ascii")
    public_key = SigningKey(private_key, encoder=HexEncoder).verify_key.encode(encoder=HexEncoder).decode("ascii")
    receiver = "receiver_public_key"
    action = "some_action"

    # Create a transaction
    tx = create_transaction(private_key, public_key, receiver, action)

    # Assert the transaction is created correctly
    assert isinstance(tx, dict)
    assert "sender" in tx and tx["sender"] == public_key
    assert "receiver" in tx and tx["receiver"] == receiver
    assert "action" in tx and tx["action"] == action
    assert "timestamp" in tx


def test_validate_transaction():
    private_key = SigningKey.generate().encode(encoder=HexEncoder).decode("ascii")
    public_key = SigningKey(private_key, encoder=HexEncoder).verify_key.encode(encoder=HexEncoder).decode("ascii")
    receiver = "receiver_public_key"
    action = "some_action"

    # Create a transaction
    tx = create_transaction(private_key, public_key, receiver, action)

    # Validate the transaction
    is_valid = validate_transaction(tx)

    # Assert the transaction is valid
    assert is_valid
