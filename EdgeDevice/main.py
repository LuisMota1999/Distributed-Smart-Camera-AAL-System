import datetime
import threading
import time
from EdgeDevice.NetworkService.Node import Node
from EdgeDevice.utils import HOST_NAME
from InferenceService.audio import AudioInference


# Disabled for compatibility with RPI
# from CaptureService.video import WebcamVideoStream
# from InferenceService.video import VideoInference


def main():
    node = Node(HOST_NAME)
    print(f"Listening on {node.ip}:{node.port}...")
    node.start()
    time.sleep(1)
    node_thread = threading.Thread(target=node.starter)
    node_thread.start()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        pass

    node.stop()
    node_thread.join()


if __name__ == '__main__':
    main()
