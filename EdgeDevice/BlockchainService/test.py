import rsa
import time
import json
import logging
from EdgeDevice.utils.helper import NetworkUtils

# Assume Alice's private and public keys are already generated
alice_private_key, alice_public_key = NetworkUtils.get_keys()

# Bob's public key (you should replace this with the actual public key)
bob_public_key_json = '{"n":1234567890123456789012345678901234567890123456789012345678901234,"e":65537}'

receiver = bob_public_key_json
action = "Payment of $100"


# Create a transaction
def create_transaction(private_key: rsa.PrivateKey, public_key: rsa.PublicKey, receiver: str, action: str):
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
    tx_bytes = json.dumps(tx, sort_keys=True).encode()

    # Sign the hash using the private key
    signature = rsa.sign(tx_bytes, private_key, 'SHA-256')

    logging.info(f"Transaction signature creation: {signature}")

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
        logging.info(f"Transaction validated!")
        return True
    except rsa.VerificationError as e:
        logging.error(f"Transaction error validating:{e.args}")
        return False


transaction, signature_tx = create_transaction(alice_private_key, alice_public_key, receiver, action)

is_valid = validate_transaction(transaction, signature_tx)

if is_valid:
    print("Transaction is valid!")
else:
    print("Transaction is not valid.")
