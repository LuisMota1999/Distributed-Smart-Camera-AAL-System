import json
import hashlib

# Função para gerar uma assinatura
def generate_signature(data):
    # Aqui estou usando uma função de hash simples (SHA-256) como exemplo.
    # Em aplicações reais, você precisaria de um método mais seguro de geração de assinaturas.
    data_str = json.dumps(data, sort_keys=True)
    signature = hashlib.sha256(data_str.encode()).hexdigest()
    return signature

# Array de transações pendentes
pending_transactions = []

# Objeto JSON que você deseja adicionar
transaction_data = {
    "sender": "Alice",
    "receiver": "Bob",
    "amount": 10.0
}

# Gere uma assinatura para o objeto JSON
transaction_signature = generate_signature(transaction_data)

# Crie um dicionário que combina o JSON e a assinatura
transaction_with_signature = {
    "data": transaction_data,
    "signature": transaction_signature
}

# Adicione o dicionário ao array de transações pendentes
pending_transactions.append(transaction_with_signature)

# Exemplo de como acessar os dados de uma transação pendente
for transaction in pending_transactions:
    data = transaction["data"]
    signature = transaction["signature"]
    print("Transaction Data:", data)
    print("Transaction Signature:", signature)
    print()
