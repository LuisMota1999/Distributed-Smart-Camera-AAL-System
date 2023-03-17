import argparse
import datetime

from capture.video import WebcamVideoStream
from inference.video import VideoInference
from utils.constants import MODEL_UNKOWN
from multiprocessing import Queue, Pool

base_url = 'http://localhost:8080/rest'

models = {
    'video': [
        {'name': 'charades', 'model': VideoInference}
    ]
}


def data_processing_worker(in_q, out_q):
    while True:
        item = in_q.get()
        for model in models[item['type']]:
            new_item = {'type': item['type'], 'name': model['name'], 'data': item['data'][:]}
            out_q.put(new_item)


def inference_worker(in_q, out_q):
    local_models = {}

    for video_model in models['video']:
        model = video_model['model']()
        local_models[video_model['name']] = model

    while True:
        item = in_q.get()
        prediction = local_models[item['name']].inference(item['data'])
        if prediction != MODEL_UNKOWN:
            out_q.put({'prediction': prediction, 'type': item['type'], 'timestamp': str(datetime.datetime.now())})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-src', '--source', dest='video_source', type=int,
                        default=0, help='Device index of the camera.')
    parser.add_argument('-wd', '--width', dest='width', type=int,
                        default=480, help='Width of the frames in the video stream.')
    parser.add_argument('-ht', '--height', dest='height', type=int,
                        default=360, help='Height of the frames in the video stream.')
    parser.add_argument('-num-w', '--num-workers', dest='num_workers', type=int,
                        default=4, help='Number of workers.')
    parser.add_argument('-q-size', '--queue-size', dest='queue_size', type=int,
                        default=5, help='Size of the queue.')
    args = parser.parse_args()

    # logger = multiprocessing.log_to_stderr()
    # logger.setLevel(multiprocessing.SUBDEBUG)

    data_captured_q = Queue(maxsize=args.queue_size)
    data_processed_q = Queue(maxsize=args.queue_size)
    prediction_q = Queue(maxsize=args.queue_size)

    processing_pool = Pool(2, data_processing_worker, (data_captured_q, data_processed_q))
    inference_pool = Pool(args.num_workers, inference_worker, (data_processed_q, prediction_q))
    # network_pool = Pool(2, network_worker, (prediction_q,))

    video_capture = WebcamVideoStream(src=args.video_source,
                                      width=args.width,
                                      height=args.height,
                                      in_q=data_captured_q)

    if video_capture.found:
        video_capture.start()

    # start the timer
    start = datetime.datetime.now()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        pass

    # stop the timer
    end = datetime.datetime.now()

    inference_pool.terminate()
    processing_pool.terminate()

    video_capture.stop()

    print('[INFO] elapsed time (seconds): {:.2f}'.format((end - start).total_seconds()))


if __name__ == '__main__':
    main()
