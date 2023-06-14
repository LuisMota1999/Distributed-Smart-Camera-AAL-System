import netifaces as ni

def get_interface_ip():
    interfaces = ni.interfaces()
    for interface in interfaces:
        if ni.AF_INET in ni.ifaddresses(interface):
            addresses = ni.ifaddresses(interface)[ni.AF_INET]
            if len(addresses) > 0:
                ip = addresses[0]['addr']
                return ip
    return None

def main():
    ip_address = get_interface_ip()
    if ip_address:
        print(f"IP Address: {ip_address}")
    else:
        print("Unable to retrieve IP address.")

if __name__ == '__main__':
    main()
