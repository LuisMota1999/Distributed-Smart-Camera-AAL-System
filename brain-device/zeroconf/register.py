import socket

# create a socket object
clientsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# get local machine name
host = "192.168.0.89"  # Replace with the IP address of machine A

port = 9999

# connect to the server
clientsocket.connect((host, port))

while True:
    # send a message to the server
    message = input("Enter a message to send to server: ")
    clientsocket.send(message.encode('ascii'))

    # receive a message from the server
    data = clientsocket.recv(1024)

    print("Received message from server: {}".format(data.decode()))

clientsocket.close()
