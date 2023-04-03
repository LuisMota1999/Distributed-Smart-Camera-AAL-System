import asyncio
from libp2p.network.network_interface import INetwork
from libp2p.network.tcp.tcp import TCP
from libp2p.host.host_interface import IHost
from libp2p.host.basic_host import BasicHost
from libp2p.discovery.discovery import Discovery
from libp2p.discovery.mdns import MDNS

async def main():
    # Create a TCP network
    network: INetwork = TCP()

    # Create a libp2p host with the TCP network
    host: IHost = BasicHost(network=network)

    # Create an MDNS discovery
    discovery: Discovery = MDNS()

    # Register the discovery with the host
    await host.network.add_listener(discovery)

    # Start the host
    await host.start()

    # Print the host ID
    print(f"Host ID: {host.get_id()}")

    # Wait for other nodes to be discovered
    await asyncio.sleep(5)

    # Discover other nodes and send a message to each of them
    for peer_info in discovery.peerstore.peers:
        if peer_info.id != host.get_id():
            await host.connect(peer_info)
            stream = await host.new_stream(peer_info, ["/echo/1.0.0"])
            await stream.write(f"Hello from {host.get_id()}".encode())
            response = await stream.read()
            print(f"Received response: {response.decode()}")
            await stream.close()

    # Close the host
    await host.close()

# Start the main function
asyncio.run(main())
