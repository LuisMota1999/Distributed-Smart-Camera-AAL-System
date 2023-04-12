import socket

# create a socket object
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# get local machine name
host = socket.gethostname()

# set a port number
port = 9999

# bind the socket to a public host, and a well-known port
server_socket.bind((host, port))

# become a server socket
server_socket.listen(1)

# wait for a client connection
print('Waiting for a client connection...')
client_socket, address = server_socket.accept()
print(f'Connected to {address}')

# send a message to the client
message = 'Hello client!'
client_socket.send(message.encode('utf-8'))

# close the socket
client_socket.close()