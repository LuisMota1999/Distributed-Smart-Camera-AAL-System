import json


def meta(from_id: str, from_ip: str, from_port: int, to_ip: str, to_port: int, version="0.0.1"):
    return {
        "CLIENT": version,
        "FROM_ADDRESS": {"ID": from_id, "IP": from_ip, "PORT": from_port},
        "TO_ADDRESS": {"IP": to_ip, "PORT": to_port},
    }


def create_election_message(internal_ip, internal_port, external_ip: str, external_port: int, coordinator: str):
    return {
        "META": meta(internal_ip, internal_port, external_ip, external_port),
        "MESSAGE": {
            "NAME": "ELECTION",
            "PAYLOAD": {
                "COORDINATOR": str(coordinator),
            },
        },
    }


def create_block_message(internal_ip, internal_port, external_ip: str, external_port: int, block):
    return {
        "META": meta(internal_ip, internal_port, external_ip, external_port),
        "MESSAGE": {"NAME": "BLOCK", "PAYLOAD": block},
    }


def create_general_message(internal_ip, internal_port, msg: str, coordinator: str, message_type: str, external_ip: str,
                           external_port: int):
    data = {
        "TYPE": message_type,
        "META": meta(internal_ip, internal_port, str(external_ip), int(external_port)),
        "MESSAGE": {
            "COORDINATOR": str(coordinator),
            "CONTENT": str(msg),
        },
    }
    return json.dumps(data)


def create_transaction_message(external_ip, external_port, internal_ip, internal_port, tx):
    return {
        "META": meta(internal_ip, internal_port, external_ip, external_port),
        "MESSAGE": {
            "NAME": "TRANSACTION",
            "PAYLOAD": tx,
        },
    }
