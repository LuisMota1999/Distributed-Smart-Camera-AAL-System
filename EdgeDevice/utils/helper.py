import uuid
import random
import datetime
from EdgeDevice.InferenceService.audio import AudioInference
import rsa
from collections import deque
import cv2
import numpy as np
from moviepy.editor import *
from pytube import YouTube

# Specify the height and width to which each video frame will be resized in our dataset
IMAGE_HEIGHT, IMAGE_WIDTH = 64, 64

# Specify the list containing the names of the classes used for training.
CLASSES_LIST = ["PushUps", "Punch", "PlayingGuitar", "HorseRace"]

models = {
    'audio': [
        {'name': 'yamnet', 'duration': 0.96, 'frequency': 16000, 'model': AudioInference, 'threshold': 0.2},
        {'name': 'yamnet_retrained', 'duration': 0.96, 'frequency': 16000, 'model': AudioInference, 'threshold': 0.6}
    ],
    'video': [
        # {'name': 'charades', 'model': VideoInference}
    ]
}


def generate_unique_id() -> str:
    """
    Generate a unique identifier by generating a UUID and selecting 10 random digits.

    :return: An string representing the unique identifier.
    """
    # Generate a UUID and convert it to a string
    uuid_str = str(uuid.uuid4())

    # Remove the hyphens and select 10 random digits
    digits = ''.join(random.choice(uuid_str.replace('-', '')) for _ in range(10))

    return digits


def data_processing_worker(in_q, out_q):
    while True:
        item = in_q.get()
        for model in models[item['type']]:
            new_item = {'type': item['type'], 'name': model['name'], 'data': item['data'][:]}
            out_q.put(new_item)


def inference_worker(in_q, out_q):
    local_models = {}
    for audio_model in models['audio']:
        model = audio_model['model'](audio_model)
        local_models[audio_model['name']] = model

    for video_model in models['video']:
        model = video_model['model']()
        local_models[video_model['name']] = model

    while True:
        item = in_q.get()
        prediction = local_models[item['name']].inference(item['data'])
        if prediction != 'Unknown':
            out_q.put({'prediction': prediction, 'type': item['type'], 'timestamp': str(datetime.datetime.now())})


def network_worker(in_q):
    while True:
        item = in_q.get()


def download_youtube_videos(youtube_video_url, output_directory):
    """
       This function downloads the YouTube video whose URL is passed to it as an argument.
       :param youtube_video_url: URL of the video that is required to be downloaded
       :param output_directory: The directory path to which the video needs to be stored after downloading
       :return title: The title of the downloaded YouTube video.
    """

    yt = YouTube(youtube_video_url)
    yt.title = yt.title.replace(' ', '_').replace('/', '').replace(',', '')

    yt.streams.filter(adaptive=True)
    output_file_path = os.path.join(output_directory)
    yt.streams.get_highest_resolution().download(output_path=output_file_path)

    return yt.title


def predict_on_video(model, video_file_path, SEQUENCE_LENGTH):
    """
    This function will perform action recognition on a video using the LRCN model
    :param model: The model to make prediction
    :param video_file_path: The path of the video stored in the disk on which the action recognition is to be performed
    :param SEQUENCE_LENGTH: The fixed number of frames of a video that can be passed to the model as one sequence.
    :return: None
    """

    # Initialize the VideoCapture object to read from the video file.
    video_reader = cv2.VideoCapture(video_file_path)

    # Declare a queue to store video frames
    frames_queue = deque(maxlen=SEQUENCE_LENGTH)

    # Initialize a variable to store the predicted action being performed in the video
    predicted_class_name = ''

    # Iterate until the video is accessed successfully
    while video_reader.isOpened():

        # Read the frame
        ok, frame = video_reader.read()

        # Check if frame is not read properly then break the loop.
        if not ok:
            break

        # Resize the frame to fixed Dimensions
        resized_frame = cv2.resize(frame, (IMAGE_HEIGHT, IMAGE_WIDTH))

        # Normalize the resized frame by diving it with 255 so that each pixel value then lies between 0 and 1
        normalized_frame = resized_frame / 255

        # Appending the pre-processed frame into the frames list
        frames_queue.append(normalized_frame)

        # Check if the number of frames in the queue are equal to the fixed sequence length.
        if len(frames_queue) == SEQUENCE_LENGTH:
            # Pass the normalized frames to the model and get the predicted probabilities
            predicted_labels_probabilities = model.predict(np.expand_dims(frames_queue, axis=0))[0]

            print("Predicted Accuracy: ", predicted_labels_probabilities)

            # Get the index of class with highest probability
            predicted_label = np.argmax(predicted_labels_probabilities)

            # Get the class name using the retrieved index
            predicted_class_name = CLASSES_LIST[predicted_label]
            break

    return predicted_class_name


def generate_keys(path, key_type):
    public_key, private_key = rsa.newkeys(1024)
    if key_type == "PUBLIC":
        with open(path, "wb") as f:
            f.write(public_key.save_pkcs1("PEM"))
    if key_type == "PRIVATE":
        with open(path, "wb") as f:
            f.write(private_key.save_pkcs1("PEM"))


def get_keys():
    current_directory = os.getcwd()
    keys_folder = os.path.join(current_directory, '..', 'Keys')

    with open(os.path.join(keys_folder, 'public.pem'), "rb") as f:
        public_key = rsa.PublicKey.load_pkcs1(f.read())

    with open(os.path.join(keys_folder, 'private.pem'), "rb") as f:
        private_key = rsa.PrivateKey.load_pkcs1(f.read())

    return private_key, public_key
