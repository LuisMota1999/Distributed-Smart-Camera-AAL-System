# import libraries
import binascii
import datetime
import collections
from Crypto.Hash import SHA
from Crypto.Signature import PKCS1_v1_5
from client import Client
import json

last_block_hash = ""


class Transaction:
    def __init__(self, sender, recipient, jsonresponse):
        self.sender = sender
        self.recipient = recipient
        self.jsonresponse = jsonresponse
        self.time = datetime.datetime.now()

    def to_dict(self):
        if self.sender == "Genesis":
            identity = "Genesis"
        else:
            identity = self.sender.identity

        return collections.OrderedDict({
            'sender': identity,
            'recipient': self.recipient,
            'jsonresponse': self.jsonresponse,
            'time': self.time})

    def sign_transaction(self):
        private_key = self.sender._private_key
        signer = PKCS1_v1_5.new(private_key)
        h = SHA.new(str(self.to_dict()).encode('utf8'))
        return binascii.hexlify(signer.sign(h)).decode('ascii')



