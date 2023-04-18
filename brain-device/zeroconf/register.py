import socket
import threading
import uuid
import time

class Peer:
    def __init__(self, host, port):
        self.id = str(uuid.uuid4())
        self.host = host
        self.port = port
        self.peers = set()

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        self.socket.listen()

        print(f"Listening on {self.host}:{self.port}...")

        # Start a thread to accept incoming connections


    def accept_connections(self):
        while True:
            conn, addr = self.socket.accept()
            print(f"Connected to {addr[0]}:{addr[1]}")

            # Start a thread to handle incoming messages
            threading.Thread(target=self.receive_message, args=(conn,)).start()

            # Add the peer to the list of connected peers
            self.peers.add(addr)

    def connect_to_peer(self, host, port):
        while True:
            try:
                conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                conn.connect((host, port))
                print(f"Connected to {host}:{port}")
                break
            except ConnectionRefusedError:
                print(f"Connection refused by {host}:{port}, retrying in 10 seconds...")
                time.sleep(10)

        # Start a thread to handle incoming messages
        threading.Thread(target=self.receive_message, args=(conn,)).start()

        # Add the peer to the list of connected peers
        self.peers.add((host, port))

    def send_message(self, message):
        for peer in self.peers:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect(peer)
            conn.sendall(message.encode())

    def receive_message(self, conn):
        while True:
            message = conn.recv(1024).decode()
            if not message:
                break
            print(f"Received message: {message}")

    def list_peers(self):
        print("Connected peers:")
        for peer in self.peers:
            print(peer)


if __name__ == "__main__":
    # Create a peer and start listening for incoming connections
    bob = Peer("192.168.122.61", 8001)
    bob.start()

    # Connect to the other peer
    bob.connect_to_peer("192.168.122.105", 8000)

    # Send a message to the other peer
    bob.send_message("Hello, Alice!")

    # Print the list of connected peers
    bob.list_peers()
