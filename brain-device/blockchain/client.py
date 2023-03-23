# import libraries
import hashlib
import random
import string
import json
import binascii
import numpy as np
import pandas as pd
import pylab as pl
import logging
import datetime
import collections
import Crypto
import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5


class Client:
    def __init__(self):
        random = Crypto.Random.new().read
        self._private_key = RSA.generate(1024, random)
        self._public_key = self._private_key.publickey()
        self._signer = PKCS1_v1_5.new(self._private_key)

    @property
    def identity(self):
        """
        The format to use for wrapping the key:

                    - *'PEM'*. (*Default*) Text encoding, done according to `RFC1421`_/`RFC1423`_.
                    - *'DER'*. Binary encoding.
                    - *'OpenSSH'*. Textual encoding, done according to OpenSSH specification.
                      Only suitable for public keys (not private keys).

        """
        return binascii.hexlify(self._public_key.exportKey(format='DER')).decode('ascii')




