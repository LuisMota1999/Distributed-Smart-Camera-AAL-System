"""

   Pubsub envelope subscriber

   Author: Guillaume Aubert (gaubert) <guillaume(dot)aubert(at)gmail(dot)com>

"""
import zmq
import socket
import json


def main():
    """ main method """

    # Prepare our context and publisher
    context    = zmq.Context()
    subscriber = context.socket(zmq.SUB)

    req = context.socket(zmq.REQ)
    req.connect("tcp://localhost:5555")

    subscriber.connect("tcp://localhost:8100")
    subscriber.setsockopt(zmq.SUBSCRIBE, b"channel-one")

    [host_name, host_ip] = get_host_name_and_ip()

    discovery_message = {
        "discovery": {
            "subscriber": {
                "header": {
                    "node_id": "213sdfsfs",
                    "node_name": host_name,
                    "node_ip": host_ip,
                    "node_port": 8100,
                    "node_group": "/device",
                    "channel_name": "premium"
                },
                "payload": {
                    "message": "subscriber_discovery_message"
                }
            }
        }
    }

    json_string = json.dumps(discovery_message)

    while True:
        req.send_multipart([b"channel-one", bytes(host_name, 'utf-8'),bytes(host_ip, 'utf-8'), bytes(str(json_string), 'utf-8')])
        message = req.recv()
        [channel, publisher_name , publisher_ip, contents ] = subscriber.recv_multipart()
        print("publisher : [%s %s %s %s]" % (channel, publisher_name , publisher_ip, contents))

    # We never get here but clean up anyhow
    subscriber.close()
    context.term()

def get_host_name_and_ip():
    try:
        host_name = socket.gethostname()
        host_ip = socket.gethostbyname(host_name)
        return [host_name, host_ip]
    except:
        print("Unable to get Hostname and IP")

if __name__ == "__main__":
    main()