import json
import time
from marshmallow import Schema, fields, validates_schema, ValidationError
from marshmallow import Schema, fields, post_load
from marshmallow_oneofschema import OneOfSchema
import uuid


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


class BlockMessage(Schema):
    PAYLOAD = fields.Nested(Block())

    @post_load
    def add_name(self, data, **kwargs):
        data["NAME"] = "BLOCK"
        return data


class TransactionMessage(Schema):
    PAYLOAD = fields.Nested(Transaction())

    @post_load
    def add_name(self, data, **kwargs):
        data["NAME"] = "TRANSACTION"
        return data


class PingMessage(Schema):
    PAYLOAD = fields.Nested(Ping())

    @post_load
    def add_name(self, data, **kwargs):
        data["NAME"] = "PING"
        return data


class ElectionMessage(Schema):
    PAYLOAD = fields.Nested(Election())


class MessageDisambiguation(OneOfSchema):
    type_field = "NAME"
    type_schemas = {
        "PING": PingMessage,
        "BLOCK": BlockMessage,
        "TRANSACTION": TransactionMessage,
        "ELECTION": ElectionMessage,
    }

    def get_obj_type(self, obj):
        if isinstance(obj, dict):
            return obj.get("NAME")


class MetaSchema(Schema):
    ADDRESS = fields.Nested(Node())
    CLIENT = fields.Str()


class BaseSchema(Schema):
    META = fields.Nested(MetaSchema())
    MESSAGE = fields.Nested(MessageDisambiguation())


def meta(ip, port, version="0.0.1"):
    return {
        "CLIENT": version,
        "ADDRESS": {"IP": ip, "PORT": port},
    }


def create_election_message(external_ip, external_port, coordinator):
    return BaseSchema().dumps(
        {
            "META": meta(external_ip, external_port),
            "MESSAGE": {
                "NAME": "ELECTION",
                "PAYLOAD": {
                    "COORDINATOR": coordinator
                },
            },
        }
    )


def create_block_message(external_ip, external_port, block):
    return BaseSchema().dumps(
        {
            "META": meta(external_ip, external_port),
            "MESSAGE": {"NAME": "BLOCK", "PAYLOAD": block},
        }
    )


def create_ping_message(external_ip, external_port, block_height, peer_count, is_miner, msg, coordinator):
    return BaseSchema().dumps(
        {
            "META": meta(external_ip, external_port),
            "MESSAGE": {
                "NAME": "PING",
                "PAYLOAD": {
                    "COORDINATOR": coordinator,
                    "BLOCK_HEIGHT": block_height,
                    "PEER_COUNT": peer_count,
                    "IS_MINER": is_miner,
                    "SEND_MSG": msg,
                },
            },
        }
    )


def create_transaction_message(external_ip, external_port, tx):
    return BaseSchema().dumps(
        {
            "META": meta(external_ip, external_port),
            "MESSAGE": {
                "NAME": "TRANSACTION",
                "PAYLOAD": tx,
            },
        }
    )

message = BaseSchema().loads(create_ping_message(190, 500, 1, 1, 1, 'abc', uuid.uuid4()).encode())
print(message)
message = message["MESSAGE"]["PAYLOAD"]

print(message["COORDINATOR"])

