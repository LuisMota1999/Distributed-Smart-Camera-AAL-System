import unittest
import time
import uuid
from EdgeDevice.NetworkService.Node import Node
from EdgeDevice.utils.helper import NetworkUtils
from unittest.mock import patch, Mock


class SocketConnectionTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        NetworkUtils.generate_keys()
        NetworkUtils.generate_tls_keys()
        cls.node = Mock(spec=Node)

    def test_connection(self):
        # Create a mock peer IP, port, and id
        peer_ip = "192.168.0.100"
        peer_port = 5000
        peer_id = "c05b94c2-c621-47e6-ad93-c3ea2f3ddc58"

        # Simulate the behavior of connect_to_peer
        self.node.connect_to_peer.return_value = None

        # Call the method that uses connect_to_peer
        result = self.node.connect_to_peer(peer_ip, peer_port, peer_id, "SALA")

        # Assertions
        self.node.connect_to_peer.assert_called_once_with(peer_ip, peer_port, peer_id, "SALA")
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
