import argparse
import datetime
import time
from multiprocessing import Queue, Pool

from CaptureService.audio import MicrophoneAudioStream
from InferenceService.audio import AudioInference

# Disabled for compatibility with RPI
# from capture.video import WebcamVideoStream
# from inference.video import VideoInference

base_url = 'http://localhost:8080/rest'

models = {
    'audio': [
        {'name': 'yamnet', 'duration': 0.96, 'frequency': 16000, 'model': AudioInference, 'threshold': 0.95},
    ],
    'video': [
        # {'name': 'charades', 'model': VideoInference}
    ]
}

last_prediction = ""


def data_processing_worker(in_q, out_q):
    while True:
        item = in_q.get()
        for model in models[item['type']]:
            new_item = {'type': item['type'], 'name': model['name'], 'data': item['data'][:]}
            out_q.put(new_item)


def inference_worker(in_q, out_q):
    local_models = {}
    last_predictions = {}  # Dictionary to store the last prediction for each model name

    for audio_model in models['audio']:
        model = audio_model['model'](audio_model)
        local_models[audio_model['name']] = model
        last_predictions[audio_model['name']] = ""  # Initialize last prediction for each model

    for video_model in models['video']:
        model = video_model['model']()
        local_models[video_model['name']] = model
        last_predictions[video_model['name']] = ""  # Initialize last prediction for each model

    while True:
        item = in_q.get()
        time.sleep(10)
        prediction = local_models[item['name']].inference(item['data'])

        if prediction != 'Unknown' and prediction != last_predictions[item['name']]:
            last_predictions[item['name']] = prediction  # Update last prediction for the current model
            print("LAST PREDICTION", last_predictions[item['name']])
            print("Current PREDICTION", prediction)
            out_q.put({'prediction': prediction, 'type': item['type'], 'timestamp': str(datetime.datetime.now())})




def network_worker(in_q):
    while True:
        item = in_q.get()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-src', '--source', dest='video_source', type=int,
                        default=0, help='Device index of the camera.')
    parser.add_argument('-wd', '--width', dest='width', type=int,
                        default=480, help='Width of the frames in the video stream.')
    parser.add_argument('-ht', '--height', dest='height', type=int,
                        default=360, help='Height of the frames in the video stream.')
    parser.add_argument('-num-w', '--num-workers', dest='num_workers', type=int,
                        default=1, help='Number of workers.')
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
    network_pool = Pool(2, network_worker, (prediction_q,))

    # Disabled for compatibility with RPI
    # video_capture = WebcamVideoStream(src=args.video_source, width=args.width, height=args.height, in_q=data_captured_q)

    # if video_capture.found:
    #    video_capture.start()

    audio_capture = MicrophoneAudioStream(src=0, in_q=data_captured_q).start()

    # start the timer
    start = datetime.datetime.now()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        pass

    # stop the timer
    end = datetime.datetime.now()

    network_pool.terminate()
    inference_pool.terminate()
    processing_pool.terminate()

    audio_capture.stop()
    # video_capture.stop()

    print('[INFO] elapsed time (seconds): {:.2f}'.format((end - start).total_seconds()))


if __name__ == '__main__':
    main()
