import rsa
import time
import json
import base64

with open("../Keys/public.pem", "rb") as f:
    public_key_data = f.read()
    public_key = rsa.PublicKey.load_pkcs1(public_key_data)

with open("../Keys/private.pem", "rb") as f:
    private_key = rsa.PrivateKey.load_pkcs1(f.read())

# Convert the public key to a Base64-encoded string
public_key_str = base64.b64encode(public_key_data).decode()
print(public_key_str)
message = {
    "receiver": "192.168.0.1",
    "amount": "tx",
    "timestamp": int(time.time()),
}
encrypted_message = json.dumps(message).encode()

decrypted_message = rsa.decrypt(encrypted_message, private_key)
print(decrypted_message.decode())

send_message = {
    "MESSAGE": encrypted_message,
    "SENDER": public_key
}

print(rsa.decrypt(send_message["MESSAGE"], private_key).decode())
