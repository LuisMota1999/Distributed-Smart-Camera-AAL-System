import unittest
import time
import uuid
from EdgeDevice.NetworkService.Node import Node


class SocketConnectionTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.node = Node("NODE-1")
        cls.node.start()  # Start the node in a separate thread

        # Wait for the node to start and establish connections
        time.sleep(2)

    @classmethod
    def tearDownClass(cls):
        cls.node.stop()  # Stop the node

    def test_connection(self):
        # Test connecting to a peer node
        peer_ip = "192.168.0.100"
        peer_port = 5000
        peer_id = uuid.uuid4()

        # Connect to the peer node
        self.node.connect_to_peer(peer_ip, peer_port, peer_id.bytes)

        # Wait for the connection to be established
        time.sleep(2)

        # Assert that the peer node is in the list of connections
        self.assertTrue(any(conn.getpeername()[0] == peer_ip and conn.getpeername()[1] == peer_port
                            for conn in self.node.connections))

    def test_disconnection(self):
        # Test disconnecting from a peer node
        peer_ip = "192.168.0.100"
        peer_port = 5000

        # Disconnect from the peer node
        for conn in self.node.connections:
            if conn.getpeername()[0] == peer_ip and conn.getpeername()[1] == peer_port:
                self.node.remove_node(conn, "Test")

        # Wait for the disconnection to complete
        time.sleep(2)

        # Assert that the peer node is not in the list of connections
        self.assertFalse(any(conn.getpeername()[0] == peer_ip and conn.getpeername()[1] == peer_port
                             for conn in self.node.connections))


if __name__ == '__main__':
    unittest.main()

