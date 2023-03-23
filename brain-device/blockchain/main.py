from client import Client
from block import Block
from transaction import Transaction
import json

if __name__ == '__main__':
    Luis = Client()
    Paulo = Client()

    data = {'key': 'value', 'local': 'test', 'abc': 'abc'}
    json_data = json.dumps(data)
    transactions = []
    t = Transaction(
        Luis,
        Paulo.identity,
        json_data
    )


    # def display_transaction(transaction):
    #     # for transaction in transactions:
    #     dict = transaction.to_dict()
    #     print("sender: " + dict['sender'])
    #     print('-----')
    #     print("recipient: " + dict['recipient'])
    #     print('-----')
    #     print("jsonresponse: " + str(dict['jsonresponse']))
    #     print('-----')
    #     print("time: " + str(dict['time']))
    #     print('-----')
    #
    #
    # signature = t.sign_transaction()
    # transactions.append(t)
    # for transaction in transactions:
    #     display_transaction(transaction)
    #     print('--------------')

    block0 = Block()
    block0.previous_block_hash = None
    block0.Nonce = None
    block0.verified_transactions.append(t)
    digest = hash (block0)
    last_block_hash = digest