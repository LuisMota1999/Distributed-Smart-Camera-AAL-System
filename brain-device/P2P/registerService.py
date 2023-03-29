import socket
from zeroconf import Zeroconf, ServiceInfo, IPVersion,ZeroconfServiceTypes

# Define the service type, name, and port number
service_type = "_myapp._tcp.local."
service_name = "MyApp_A"
service_port = 8008

# Get the IP address of the Wi-Fi interface
ip_address = socket.gethostbyname(socket.gethostname())

# Create a Zeroconf instance
# Register the service
zc= Zeroconf(ip_version=IPVersion.V4Only)

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
print(f"Service {service_name} running on {ip_address}:{service_port}")
print('\n'.join(ZeroconfServiceTypes.find()))

print("Waiting for connection...")
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((ip_address, service_port))
server_socket.listen(1)
conn, addr = server_socket.accept()
print("Connected by", addr)

# Exchange messages
while True:
    data = conn.recv(1024)
    if not data:
        break
    print("Received message from Peer B:", data.decode())
    message = input("Enter message to send to Peer B: ")
    conn.sendall(message.encode())

# Wait for a connection
input("Press enter to exit...\n")

# Unregister the service
zc.unregister_service(service_info)

