from marshmallow import Schema, fields, post_load
from marshmallow_oneofschema import OneOfSchema
from ..BlockchainService.Schema import Block, Transaction, Ping, Election, Node


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
    return {
        "META": meta(external_ip, external_port),
        "MESSAGE": {
            "NAME": "ELECTION",
            "PAYLOAD": {
                "COORDINATOR": coordinator
            },
        },
    }


def create_block_message(external_ip, external_port, block):
    return {
        "META": meta(external_ip, external_port),
        "MESSAGE": {"NAME": "BLOCK", "PAYLOAD": block},
    }


def create_ping_message(msg, coordinator):
    return {
        "TYPE": "PING",
        "MESSAGE": {
            "COORDINATOR": coordinator,
            "CONTENT": msg
        },
    }


def create_transaction_message(external_ip, external_port, tx):
    return {
        "META": meta(external_ip, external_port),
        "MESSAGE": {
            "NAME": "TRANSACTION",
            "PAYLOAD": tx,
        },
    }
