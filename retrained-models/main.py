from collections import deque

import cv2
import numpy as np
import tensorflow as tf
from moviepy.editor import *
from pytube import YouTube

# Specify the height and width to which each video frame will be resized in our dataset
IMAGE_HEIGHT, IMAGE_WIDTH = 64, 64

# Specify the list containing the names of the classes used for training.
CLASSES_LIST = ["PushUps", "Punch", "PlayingGuitar", "HorseRace"]


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


def predict_on_video(LRCN_MODEL, video_file_path, output_file_path, SEQUENCE_LENGTH):
    """
    This function will perform action recognition on a video using the LRCN model
    :param video_file_path: The path of the video stored in the disk on which the action recognition is to be performed
    :param output_file_path: The path where the output video with the predicted action being performed overlayed will be stored
    :param SEQUENCE_LENGTH: The fixed number of frames of a video that can be passed to the model as one sequence.
    :return: None
    """

    # Initialize the VideoCapture object to read from the video file.
    video_reader = cv2.VideoCapture(video_file_path)

    # Get the width and height of the video
    original_video_width = int(video_reader.get(cv2.CAP_PROP_FRAME_WIDTH))
    original_video_height = int(video_reader.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Initialize the VideoWriter Object to store the output video in the disk
    video_writer = cv2.VideoWriter(output_file_path, cv2.VideoWriter_fourcc('M', 'P', '4', 'V'),
                                   video_reader.get(cv2.CAP_PROP_FPS), (original_video_width, original_video_height))

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
            predicted_labels_probabilities = LRCN_MODEL.predict(np.expand_dims(frames_queue, axis=0))[0]

            # Get the index of class with highest probability
            predicted_label = np.argmax(predicted_labels_probabilities)

            # Get the class name using the retrieved index
            predicted_class_name = CLASSES_LIST[predicted_label]

        # Write predicted class name on top of the frame
        cv2.putText(frame, predicted_class_name, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Write the frame into the disk using the VideoWriter object
        video_writer.write(frame)

    # Release the VideoCapture and VideoWriter object
    video_reader.release()
    video_writer.release()


def main():
    # Make the output directory if it does not exist
    test_videos_directory = 'test_videos'
    os.makedirs(test_videos_directory, exist_ok=True)

    # Download a YouTube video
    video_title = download_youtube_videos('https://youtube.com/watch?v=iNfqx2UCu-g', test_videos_directory)
    print(f"Downloaded video title: {video_title}")

    # Get the YouTube video's path we just downloaded
    input_video_file_path = f'{test_videos_directory}/{video_title}.mp4'

    # Construct the output video path
    output_video_file_path = f'{test_videos_directory}/{video_title}-Output-SeqLen{20}.mp4'

    # Load Model
    model = tf.keras.models.load_model(
        '../EdgeDevice/models/LRCN_model__Date_time_2023_05_23__00_06_42__Loss_0.23791147768497467__Accuracy_0.971222996711731.h5')

    # Perform action recognition on the test video
    predict_on_video(model, input_video_file_path, output_video_file_path, 20)


if __name__ == '__main__':
    main()
