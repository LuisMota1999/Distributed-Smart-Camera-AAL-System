import rsa
import time
import json
import logging
from EdgeDevice.utils.helper import NetworkUtils


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
        "SENDER": NetworkUtils.key_to_json(public_key),
        "RECEIVER": receiver,
        "EVENT": action,
        "TIMESTAMP": int(time.time()),
    }
    tx_bytes = json.dumps(tx, sort_keys=True).encode('utf-8')

    # Compute the hash of the data using SHA-256
    hash_value = rsa.compute_hash(tx_bytes, 'SHA-256')

    # Sign the hash using the private key
    signature = rsa.sign(hash_value, private_key, 'SHA-256')

    logging.info(f"Transaction signature creation: {signature}")
    tx["SIGNATURE"] = signature.hex()
    try:
        # Verify the signature using the public key
        rsa.verify(tx_bytes, signature, public_key)
        print("Signature is valid.")
    except rsa.VerificationError:
        print("Signature is invalid.")
    return tx


def validate_transaction(tx):
    """
    Verifies that a given transaction was sent from the sender

    :param tx: The transaction dict
    :type tx: dict
    :return: True if the transaction is valid, False otherwise
    :rtype: bool
    """

    public_key_pem = tx['SENDER']
    public_key = NetworkUtils.load_key_from_json(public_key_pem)
    tx_bytes = json.dumps(tx, sort_keys=True).encode('utf-8')
    signature = bytes.fromhex(tx['SIGNATURE'])
    hash_value = rsa.compute_hash(tx_bytes, 'SHA-256')

    try:
        rsa.verify(hash_value, signature, public_key)
        logging.info(f"Transaction validated!")
        return True
    except rsa.VerificationError as e:
        logging.error(f"Transaction error validating:{e.args}")
        return False

