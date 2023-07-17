import rsa
import time
import json

from EdgeDevice.utils.helper import key_to_json, load_key_from_json


def create_transaction(private_key, public_key, receiver, action):
    """
    Creates a transaction from a sender's public key to a receiver's public key

    :param private_key: The Sender's private key
    :type private_key: rsa.PrivateKey
    :param public_key: The Sender's public key
    :type public_key: rsa.PublicKey
    :param receiver: The Receiver's public key
    :type receiver: str
    :param action: The action performed in real time in a certain point in time by the user
    :type action: str
    :return: The transaction dict
    :rtype: dict
    """
    tx = {
        "sender": key_to_json(public_key),
        "receiver": receiver,
        "action": action,
        "timestamp": int(time.time()),
    }
    tx_bytes = json.dumps(tx, sort_keys=True).encode("ascii")

    signature = rsa.sign(tx_bytes, private_key, "SHA-256")
    tx["signature"] = signature.hex()

    return tx


def validate_transaction(tx):
    """
    Verifies that a given transaction was sent from the sender

    :param tx: The transaction dict
    :type tx: dict
    :return: True if the transaction is valid, False otherwise
    :rtype: bool
    """
    public_key_pem = tx["sender"].encode()
    public_key = load_key_from_json(public_key_pem)

    tx_bytes = json.dumps(tx, sort_keys=True).encode("ascii")

    # Retrieve the signature from the transaction
    signature = bytes.fromhex(tx["signature"])

    # Verify the signature using the public key
    try:
        rsa.verify(tx_bytes, signature, public_key)
        return True
    except rsa.pkcs1.VerificationError:
        return False
