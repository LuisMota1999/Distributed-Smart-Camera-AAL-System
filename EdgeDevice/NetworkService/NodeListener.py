import logging

from zeroconf import Zeroconf, ServiceStateChange
from typing import cast


class NodeListener:
    def __init__(self, node):
        """
        Initializes a new instance of the NodeListener class.

        :param node: An instance of the Node class representing the local node that will use this listener.
        """
        self.node = node

    def add_service(self, zeroconf, service_type, name):
        """
        Adds a service to the node's peer list, if it is not already present.

        This method retrieves the IP addresses of the service and adds them as peers, if they are different from
        the IP address of the node itself. It uses the Zeroconf instance to get the service information.

        :param zeroconf: The Zeroconf instance that discovered the service.
        :type zeroconf: <Zeroconf>
        :param service_type: The type of the service, e.g. "_node._tcp.local.".
        :type service_type: <str>
        :param name: The name of the service, e.g. "Node-X".
        :type name: <str>
        """
        info = zeroconf.get_service_info(service_type, name)
        if info:
            ip_list = info.parsed_addresses()
            for ip in ip_list:
                if ip != self.node.ip:
                    self.node.connect_to_peer(ip, info.port, info.properties.get(b'ID'), info.properties.get(b'LOCAL'))

    def update_service(self,
                       zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange
                       ) -> None:
        """
        The `update_service` method is called by the `Zeroconf` instance when a service is added, removed,
        or updated on the network. It takes several arguments:

        :param zeroconf: A `Zeroconf` instance representing the local network.
        :type zeroconf: `<Zeroconf>`
        :param service_type: The type of the service that was updated, specified as a string in the format "<protocol>._
                            <transport>.local." (e.g. "_node._tcp.local.").
        :type service_type: `<str>`
        :param name: The name of the service that was updated, as a string.
        :type name: `<str>`
        :param state_change: An enum indicating the type of change that occurred one of "Added", "Updated", or "Removed"
        :type state_change: `<ServiceStateChange>`

        If the `state_change` is "Added" or "Updated", the method calls the `add_service` method to add the updated
        service to the network. Otherwise, the service is removed from the network.
        """
        logging.info(f"Service {name} of type {service_type} state changed: {state_change}")

        if state_change is ServiceStateChange.Added or ServiceStateChange.Updated:
            info = zeroconf.get_service_info(service_type, name)
            if info:
                addresses = ["%s:%d" % (addr, cast(int, info.port)) for addr in info.parsed_addresses()]
                print("  Addresses: %s" % ", ".join(addresses))
                print("  Weight: %d, priority: %d" % (info.weight, info.priority))
                print(f"  Server: {info.server}")
                if info.properties:
                    print("  Properties are:")
                    for key, value in info.properties.items():
                        print(f"    {key}: {value}")
                else:
                    print("  No properties")
                self.add_service(zeroconf, service_type, name)
            else:
                print("  No info")
            print('\n')
