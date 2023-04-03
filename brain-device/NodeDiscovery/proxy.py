from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf
import Pyro4
import Pyro4.naming
import threading
import socket
import time


class NodeDiscovery(threading.Thread):
    def __init__(self):
        super().__init__()
        self.discovered_nodes = []
        self.zeroconf = Zeroconf()
        self.listener = NodeListener(self)
        self.running = True

    def run(self):
        browser = ServiceBrowser(self.zeroconf, "_node._tcp.local.", [self.listener.update_service])
        while self.running:  # check running flag
            # do some background work here, if any
            pass

    def stop(self):
        self.running = False
        self.zeroconf.close()

    def add_node(self, uri):
        if uri not in self.discovered_nodes:
            self.discovered_nodes.append(uri)
            print(f"Node {uri} added to the network")
            print(f"Discovered nodes: {self.discovered_nodes}")

    def remove_node(self, uri):
        if uri in self.discovered_nodes:
            self.discovered_nodes.remove(uri)
            print(f"Node {uri} removed from the network")
            print(f"Discovered nodes: {self.discovered_nodes}")


class NodeListener:
    def __init__(self, node_discovery):
        self.node_discovery = node_discovery

    def remove_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if info:
            uri = Pyro4.URI(f"PYRO:{info.server.lower()}:{info.port}")
            self.node_discovery.remove_node(uri)

    def add_service(self, zeroconf, type, name):

        info = zeroconf.get_service_info(type, name)
        if info:
            uri = Pyro4.URI(f"PYRO:{info.server.lower()}:{info.port}")
            self.node_discovery.add_node(uri)

    def update_service(self, zeroconf, service_type, name, state_change):
        print(f"Service update: {service_type} {name} {state_change}")
        self.add_service(zeroconf, service_type, name)


class Node:
    def __init__(self, name):
        self.name = name
        self.uri = None
        self.discovered_nodes = []
        self.daemon = Pyro4.Daemon()
        self.ns = Pyro4.naming.locateNS()

    @Pyro4.expose
    def add_node(self, uri):
        if uri not in self.discovered_nodes:
            self.discovered_nodes.append(uri)
            print(f"Node {uri} added to the network")

    @Pyro4.expose
    def send_message(self, message, recipient_uri):
        print(f"Sending message '{message}' to {recipient_uri}")
        proxy = Pyro4.Proxy(recipient_uri)
        proxy.receive_message(message, self.uri)

    @Pyro4.expose
    def receive_message(self, message, sender_uri):
        print(f"Received message '{message}' from {sender_uri}")

    @Pyro4.expose
    def get_discovered_nodes(self):
        return self.discovered_nodes

    @Pyro4.expose
    def connect_to_node(self, node_name):
        uri = self.ns.lookup(node_name)
        self.send_message(f"Hello, {node_name}!", uri)

    def start(self):
        self.uri = self.daemon.register(self)
        service_info = ServiceInfo(
            type_="_node._tcp.local.",
            name=f"{self.name}._node._tcp.local.",
            port=self.daemon.sock.getsockname()[1],
            weight=0,
            priority=0,
            properties={},
        )
        zeroconf = Zeroconf()
        zeroconf.register_service(service_info)
        print(f"Node {self.name} registered service: {service_info}")
        self.ns.register(self.name, self.uri)
        print(f"Node {self.name} registered Pyro4 object: {self.uri}")
        self.daemon.requestLoop()

    def join(self, node_uri):
        proxy = Pyro4.Proxy(node_uri)
        while self.uri not in proxy.get_discovered_nodes():
            time.sleep(1)
        print(f"Node {self.name} joined the network")

#pyro4-ns
if __name__ == "__main__":
    node1 = Node("node1")
    node2 = Node("node2")
    node_discovery = NodeDiscovery()  # Start NodeDiscovery thread
    node_discovery.start()

    time.sleep(1)  # Wait for discovery process to happen

    node1_thread = threading.Thread(target=node1.start)  # Start Node 1 thread
    node2_thread = threading.Thread(target=node2.start)  # Start Node 2 thread

    node1_thread.start()
    node2_thread.start()

    node1_thread.join()
    node2_thread.join()

    print("Discovery stops!")
    discovered_nodes = node_discovery.discovered_nodes
    print(discovered_nodes)

    node_discovery.stop()
    time.sleep(1)  # Wait for discovery process to stop
    node1.connect_to_node("node2")

    node1.send_message("Hello, Node 2!", node2.uri)  # Send a message from Node 1 to Node 2



