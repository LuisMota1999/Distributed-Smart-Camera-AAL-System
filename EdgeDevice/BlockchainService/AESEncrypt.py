from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import json

salt = get_random_bytes(256)

password = "mypassword"
key = PBKDF2(password, salt, dkLen=32)

message = {
    'META': {
        'CLIENT': '0.0.1',
        'FROM_ADDRESS': {'ID': 'dfd25ee1-8f3c-43f2-bd83-bd0842f20509', 'IP': '192.168.122.106', 'PORT': 5587},
        'TO_ADDRESS': {'IP': '192.168.122.249', 'PORT': 5003}
    },
    'TYPE': 'PING',
    'PAYLOAD': {
        'LAST_TIME_ALIVE': 1686058643.96257,
        'COORDINATOR': '5d5af111-a75f-4298-a532-88118021209e',
        'PUBLIC_KEY': 'LS0tLS1CRUdJTiBSU0EgUFVCTElDIEtFWS0tLS0tCk1JR0pBb0dCQU1CY0c3d0dGVEovQVVHNWxGdGwrd3V6akVNek0rNkZNV1lCK080dTNESzVEcW5lRDlmVzBCT0kKY25GSUtBY0dvc1dVdHBZVnVPTWRwQWFRaDBSWlJDc25nOE1DVXQvMWR0NWJqbFZiVXFmUSs3MGFTQllKZ1ZScApHY0lqTzhSdFJnRnF0YzhKNm5iZnlHZ0dNbnhGaXhjM20yMnVxQnBZUGpiZ1ZIQUFJSTdYQWdNQkFBRT0KLS0tLS1FTkQgUlNBIFBVQkxJQyBLRVktLS0tLQo='
    }
}
cipher = AES.new(key, AES.MODE_CBC)
cipher_data = cipher.encrypt(pad(json.dumps(message).encode(), AES.block_size))
print(cipher_data)
