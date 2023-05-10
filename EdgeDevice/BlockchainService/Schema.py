import json
import time
from marshmallow import Schema, fields, validates_schema, ValidationError


class Transaction(Schema):
    TIMESTAMP = fields.Int()
    SENDER = fields.Str()
    RECEIVER = fields.Str()
    AMOUNT = fields.Int()
    SIGNATURE = fields.Str()

    class Meta:
        ordered = True


class Block(Schema):
    MINED_BY = fields.Str(required=False)
    TRANSACTIONS = fields.Nested(Transaction(), many=True)
    HEIGHT = fields.Int(required=True)
    TARGET = fields.Str(required=True)
    HASH = fields.Str(required=True)
    PREVIOUS_HASH = fields.Str(required=True)
    NONCE = fields.Str(required=True)
    TIMESTAMP = fields.Int(required=True)

    class Meta:
        ordered = True

    @validates_schema
    def validate_hash(self, data, **kwargs):
        block = data.copy()
        block.pop("hash")

        if data["hash"] != json.dumps(block, sort_keys=True):
            raise ValidationError("Fraudulent block: hash is wrong")


class Node(Schema):
    IP = fields.Str(required=True)
    PORT = fields.Int(required=True)
    LAST_SEEN = fields.Int(missing=lambda: int(time.time()))


class Ping(Schema):
    BLOCK_HEIGHT = fields.Int(required=False)
    PEER_COUNT = fields.Int(required=False)
    IS_MINER = fields.Bool(required=False)
    SEND_MSG = fields.Str()
    COORDINATOR = fields.UUID()

    class Meta:
        ordered = True


class Election(Schema):
    COORDINATOR = fields.UUID(required=True)