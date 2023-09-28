import rsa
import time
import json
import logging
from EdgeDevice.utils.helper import NetworkUtils


def create_transaction(private_key: rsa.PrivateKey, public_key: rsa.PublicKey, receiver: str, action: str, type: str,
                       local: str, precision: str):
    """
    Creates a transaction from a sender's public key to a receiver's public key

    :param type: Type of transaction
    :type type: str
    :param precision: Score from activity classification
    :type precision: str
    :param private_key: The Sender's private key
    :type private_key: rsa.PrivateKey
    :param public_key: The Sender's public key
    :type public_key: rsa.PublicKey
    :param receiver: The Receiver's public key
    :type receiver: str
    :param action: The action performed in real time in a certain point in time by the user
    :type action: str
    :param local: The local the sensor is at smart home
    :type local: str
    :return: The transaction dict
    :rtype: dict
    """
    tx = {
        "SENDER": NetworkUtils.key_to_json(public_key),
        "RECEIVER": receiver,
        "EVENT_TYPE": type,
        "EVENT_ACTION": action,
        "EVENT_LOCAL": local,
        "PRECISION": precision,
        "TIMESTAMP": int(time.time()),
    }
    tx_bytes = json.dumps(tx, sort_keys=True).encode()

    # Sign the hash using the private key
    signature = rsa.sign(tx_bytes, private_key, 'SHA-256')

    return tx, signature.hex()


def validate_transaction(transaction: dict, signature_hex: str):
    """
    Verifies that a given transaction was sent from the sender

    :param signature_hex: The signature of transaction
    :type signature_hex: str
    :param transaction: The transaction dict
    :type transaction: dict
    :return: True if the transaction is valid, False otherwise
    :rtype: bool
    """

    public_key_pem = transaction['SENDER']
    public_key = NetworkUtils.load_key_from_json(public_key_pem)
    tx_bytes = json.dumps(transaction, sort_keys=True).encode()
    signature = bytes.fromhex(signature_hex)

    try:
        rsa.verify(tx_bytes, signature, public_key)
        return True
    except rsa.VerificationError as e:
        logging.error(f"Transaction error validating:{e.args}")
        return False
