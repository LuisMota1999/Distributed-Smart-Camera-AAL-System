import cv2
import time
from threading import Thread


class WebcamVideoStream:
    def __init__(self, src, width, height, in_q):
        # initialize the video camera stream and read the first frame from the stream
        self.stream = cv2.VideoCapture(src)
        self.found = True

        if self.stream is None or not self.stream.isOpened():
            print("[VIDEO] Webcam not available!")
            self.found = False
            return

        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        _, _ = self.stream.read()

        self.in_q = in_q

        # initialize the variable used to indicate if the thread should be stopped
        self.running = False

    def start(self):
        self.running = True

        # start the thread to read frames from the video stream, and the thread to process the frames
        self.thread = Thread(target=self.update, args=())
        self.thread.start()

        return self

    def update(self):
        # keep looping infinitely until the thread is stopped
        while self.running:

            # otherwise, read the next frame from the stream
            _, frame = self.stream.read()

            item = {"type": "video", 'data': frame}
            self.in_q.put(item)

            t = time.time()

            # cv2.imshow('Video', cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

            # print('[INFO] elapsed time: {:.2f}'.format(time.time() - t))

            if cv2.waitKey(500) & 0xFF == ord('q'):
                break

    def stop(self):
        # indicate that the thread should be stopped
        self.running = False
        self.thread.join()
        cv2.destroyAllWindows()
