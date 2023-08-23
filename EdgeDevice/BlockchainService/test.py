import rsa
import time
import json
from EdgeDevice.utils.helper import NetworkUtils

private_key, public_key = NetworkUtils.get_keys()

tx = {
    'SENDER': NetworkUtils.key_to_json(public_key),
    'RECEIVER': "receiver",
    'EVENT': "event",
    'TIMESTAMP': int(time.time()),
}
tx_bytes = json.dumps(tx, sort_keys=True).encode()

signature = rsa.sign(tx_bytes, private_key, 'SHA-256')

print(rsa.verify(tx_bytes, signature, public_key))

