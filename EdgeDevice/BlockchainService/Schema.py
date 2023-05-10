import json
import time

from marshmallow import Schema, fields, validates_schema, ValidationError


class Transaction(Schema):
    timestamp = fields.Int()
    sender = fields.Str()
    receiver = fields.Str()
    amount = fields.Int()
    signature = fields.Str()

    class Meta:
        ordered = True


class Block(Schema):
    mined_by = fields.Str(required=False)
    transactions = fields.Nested(Transaction(), many=True)
    height = fields.Int(required=True)
    target = fields.Str(required=True)
    hash = fields.Str(required=True)
    previous_hash = fields.Str(required=True)
    nonce = fields.Str(required=True)
    timestamp = fields.Int(required=True)

    class Meta:
        ordered = True

    @validates_schema
    def validate_hash(self, data, **kwargs):
        block = data.copy()
        block.pop("hash")

        if data["hash"] != json.dumps(block, sort_keys=True):
            raise ValidationError("Fraudulent block: hash is wrong")


class Node(Schema):
    ip = fields.Str(required=True)
    port = fields.Int(required=True)
    last_seen = fields.Int(missing=lambda: int(time.time()))


class Ping(Schema):
    block_height = fields.Int(required=True)
    peer_count = fields.Int(required=False)
    is_miner = fields.Bool(required=False)
    SEND_MSG = fields.Str()
    COORDINATOR = fields.UUID()


class Election(Schema):
    coordinator = fields.UUID(required=True)
