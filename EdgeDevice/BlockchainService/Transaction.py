import logging
from time import time
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

from EdgeDevice.utils.helper import load_key_from_json


def create_transaction(private_key, public_key, receiver, action):
    """
    Creates a transaction from a sender's public key to a receiver's public key

    :param private_key: The Sender's private key
    :type private_key: cryptography.hazmat.primitives.asymmetric.rsa.RSAPrivateKey
    :param public_key: The Sender's public key
    :type  public_key: cryptography.hazmat.primitives.asymmetric.rsa.RSAPublicKey
    :param receiver: The Receiver's public key
    :type  receiver: str
    :param action: The action performed in real time in a certain point in time by the user
    :type  action: str
    :return: The transaction dict
    :rtype: dict
    """
    timestamp = int(time())

    message = f"{public_key}{receiver}{action}{timestamp}".encode()
    signature = private_key.sign(message,
                                 padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                                 hashes.SHA256())

    tx = {
        "sender": public_key.public_bytes(encoding=serialization.Encoding.PEM,
                                          format=serialization.PublicFormat.SubjectPublicKeyInfo).decode(),
        "receiver": receiver,
        "action": action,
        "timestamp": timestamp,
        "signature": signature.hex()
    }

    return tx


def validate_transaction(tx):
    """
    Verifies that a given transaction was sent from the sender

    :param tx: The transaction dict
    :type tx: dict
    :return: True if the transaction is valid, False otherwise
    :rtype: bool
    """
    public_key = load_key_from_json(tx["sender"].encode())

    try:
        message = f"{tx['sender']}{tx['receiver']}{tx['action']}{tx['timestamp']}".encode()
        public_key.verify(bytes.fromhex(tx["signature"]), message,
                          padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                          hashes.SHA256())
        return True
    except Exception as e:
        logging.error(f"Validate Transaction: {e.args}")
        return False
