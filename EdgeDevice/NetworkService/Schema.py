import json
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
        block.pop("HASH")

        if data["HASH"] != json.dumps(block, sort_keys=True):
            raise ValidationError("Fraudulent block: hash is wrong")
