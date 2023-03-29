import socket
import zeroconf
from zeroconf import Zeroconf, ServiceInfo,IPVersion

# Define the service type, name, and port number
service_type = "_myapp._tcp.local."
service_name = "MyApp_B"
service_port = 8008

# Get the IP address of the Wi-Fi interface
ip_address = socket.gethostbyname(socket.gethostname())

# Create a Zeroconf instance
# Register the service
zc = Zeroconf(ip_version=IPVersion.V4Only)

# Register the service
# Register the service
service_info = ServiceInfo(
    service_type,
    f"{service_name}.{service_type}",
    addresses=[socket.inet_aton(ip_address)],
    port=service_port,
    properties={},
    server=f"{service_name}.local."
)
zc.register_service(service_info)

# Connect to Peer A
print("Connecting to Peer A...")
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((ip_address, service_port))

# Exchange messages
while True:
    message = input("Enter message to send to Peer A: ")
    client_socket.sendall(message.encode())
    data = client_socket.recv(1024)
    if not data:
        break
    print("Received message from Peer A:", data.decode())

# Close the connection
client_socket.close()

# Unregister the service
zc.unregister_service(service_info)
