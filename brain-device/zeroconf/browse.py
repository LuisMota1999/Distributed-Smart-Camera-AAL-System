from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf, ServiceStateChange, ZeroconfServiceTypes, IPVersion
import Pyro4
import Pyro4.naming
import threading
import socket
import time
import argparse
import logging
from time import sleep
from typing import cast


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
            # send keep-alive messages to all discovered nodes
            for uri in self.discovered_nodes:
                try:
                    proxy = Pyro4.Proxy(uri)
                    proxy.ping()
                except Pyro4.errors.CommunicationError:
                    # node is no longer available
                    self.remove_node(uri)
            time.sleep(10)  # send keep-alive messages every 10 seconds
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
        print(info)
        if info:
            uri = Pyro4.URI(f"PYRO:{info.server.lower()}:{info.port}")
            self.node_discovery.add_node(uri)

    def update_service(self, zeroconf, service_type, name, state_change):
        print(f"Service update: {service_type} {name} {state_change}")
        self.add_service(zeroconf, service_type, name)

    def update_service(self,
                       zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange
                       ) -> None:
        print(f"Service {name} of type {service_type} state changed: {state_change}")

        if state_change is ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            print("Info from zeroconf.get_service_info: %r" % (info))

            if info:
                addresses = ["%s:%d" % (addr, cast(int, info.port)) for addr in info.parsed_scoped_addresses()]
                print("  Addresses: %s" % ", ".join(addresses))
                print("  Weight: %d, priority: %d" % (info.weight, info.priority))
                print(f"  Server: {info.server}")
                if info.properties:
                    print("  Properties are:")
                    for key, value in info.properties.items():
                        print(f"    {key}: {value}")
                else:
                    print("  No properties")
            else:
                print("  No info")
            print('\n')


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

        if args.debug:
            logging.getLogger('zeroconf').setLevel(logging.DEBUG)
        if args.v6:
            ip_versionX = IPVersion.All
        elif args.v6_only:
            ip_versionX = IPVersion.V6Only
        else:
            ip_versionX = IPVersion.V4Only

        print(self.daemon.sock.getsockname()[1])
        self.uri = self.daemon.register(self)
        service_info = ServiceInfo(
            type_="_node._tcp.local.",
            name=f"{self.name}._node._tcp.local.",
            addresses=[socket.inet_aton("127.0.0.1")],
            port=self.daemon.sock.getsockname()[1],
            weight=0,
            priority=0,
            properties={},
        )

        zc = Zeroconf(ip_version=ip_versionX)
        zc.register_service(service_info)
        print(f"Node {self.name} registered service: {service_info}")
        self.ns.register(self.name, self.uri)
        print(f"Node {self.name} registered Pyro4 object: {self.uri}")
        self.daemon.requestLoop()

    def join(self, node_uri):
        proxy = Pyro4.Proxy(node_uri)
        while self.uri not in proxy.get_discovered_nodes():
            time.sleep(1)
        print(f"Node {self.name} joined the network")


# pyro4-ns
if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--find', action='store_true', help='Browse all available services')
    version_group = parser.add_mutually_exclusive_group()
    version_group.add_argument('--v6', action='store_true')
    version_group.add_argument('--v6-only', action='store_true')
    args = parser.parse_args()

    if args.debug:
        logging.getLogger('zeroconf').setLevel(logging.DEBUG)
    if args.v6:
        ip_version = IPVersion.All
    elif args.v6_only:
        ip_version = IPVersion.V6Only
    else:
        ip_version = IPVersion.V4Only

    node1 = Node("node1")
    node2 = Node("node2")
    node3 = Node("node3")
    node4 = Node("node4")
    node_discovery = NodeDiscovery()  # Start NodeDiscovery thread
    node_discovery.start()

    time.sleep(1)  # Wait for discovery process to happen

    node1_thread = threading.Thread(target=node1.start)  # Start Node 1 thread
    node2_thread = threading.Thread(target=node2.start)  # Start Node 2 thread
    node3_thread = threading.Thread(target=node3.start)  # Start Node 3 thread
    node4_thread = threading.Thread(target=node4.start)  # Start Node 4 thread

    node1_thread.start()
    node2_thread.start()
    node3_thread.start()
    node4_thread.start()

    time.sleep(5)  # Wait for all nodes to start and register their services

    discovered_nodes = node_discovery.discovered_nodes
    print(discovered_nodes)

    node1.connect_to_node("node2")
    ## Falta colocar uma helper function pra descobrir qual o nó que deve procurar comunicar p.ex
    node1.send_message("Ola teste", node2.uri)
    node1_thread.join()
    node2_thread.join()
    node3_thread.join()
    node4_thread.join()

    node_discovery.stop()
    time.sleep(1)  # Wait for discovery process to stop
