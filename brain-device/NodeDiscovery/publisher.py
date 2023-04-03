import Pyro4
from proxy import NodeDiscovery

class NodeB:
    def __init__(self):
        self.name = "nodeB"

    def send_message(self, message):
        print(f"Received message: {message}")

if __name__ == "__main__":
    node_b = NodeB()
    node_b_uri = Pyro4.Daemon().register(node_b)

    # connect to Node Discovery service
    discovery = NodeDiscovery()
    discovery.add_node(node_b_uri)

    # print("Node B ready to receive messages.")
    # Pyro4.Daemon().requestLoop()

    node_a_uri = discovery.get_node_uri("nodeA")

