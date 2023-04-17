import socket
import threading
import time

# Machine A IP address and port number
IP_A = '192.168.122.94'
PORT_A = 5000

# Machine B IP address and port number
IP_B = '192.168.122.15'
PORT_B = 5000

# Initialize the socket object
sock_b = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock_b.bind((IP_B, PORT_B))
sock_b.listen()

def send_a():
    # Retry for up to 10seconds
    for i in range(10):
        try:
            # Connect to Machine B
            sock_a = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock_a.connect((IP_A, PORT_A))

            while True:
                # Send a message to Machine B
                message = input("Enter a message to send to Machine A: ")
                sock_a.send(message.encode())

                # Receive a response from Machine B
                response = sock_a.recv(1024).decode()
                print(f"Received from Machine A: {response}")
            # Close the socket
            sock_a.close()
            break  # Exit the retry loop if successful

        except ConnectionRefusedError:
            print(f"Connection refused. Retrying in 1 second ({i+1}/10 attempts).")
            time.sleep(1)

    else:
        raise RuntimeError("Could not establish connection to Machine B.")

def receive_b():
    # Wait for incoming connections
    conn, addr = sock_b.accept()
    print(f"Connection from {addr}")

    while True:
        # Receive a message from Machine B
        message = conn.recv(1024).decode()
        print(f"Received from Machine B: {message}")

        # Send a response to Machine B
        response = input("Enter a message to send to Machine B: ")
        conn.send(response.encode())

    # Close the connection
    conn.close()

# Start the send_b thread
send_thread = threading.Thread(target=send_a)
send_thread.start()

# Start the receive_a thread
receive_thread = threading.Thread(target=receive_b)
receive_thread.start()

# Wait for both threads to finish
send_thread.join()
receive_thread.join()

# Close the socket
sock_b.close()
