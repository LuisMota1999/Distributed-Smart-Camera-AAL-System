# https://www.youtube.com/watch?v=QmtSkq3DYko&ab_channel=BleedAIAcademy
import os
import cv2
import pafy
import math
import random
import numpy as np
import datetime as dt
import tensorflow as tf
from collections import deque
import matplotlib.pyplot as plt
import requests, zipfile
from io import StringIO
from moviepy.editor import *
from sklearn.model_selection import train_test_split
import tensorflow as tf
import keras
# Allow us to control the randomness
seed_constant = 27
np.random.seed(seed_constant)
tf.random.set_seed(seed_constant)

zip_file_url = "https://www.crcv.ucf.edu/data/UCF50.rar"

r = requests.get(zip_file_url, stream=True)
z = zipfile.ZipFile(StringIO(r.content))
z.extractall("./datasets/UCF50/")

# Create a Matplotlib figure and specify the size of the figure
plt.figure(figsize = (20,20))

# Get the names of all classes/categories in UCF50
all_classes_names = os.listdir('./datasets/UCF50/')

# Generate a list of 20 random values. The values will be between 0-50,
# where 50 is the total number of class in the dataset.
random_range = random.sample(range(len(all_classes_names)),20)

# Iterating through all the generated random values.
for counter, random_index in enumerate(random_range,1):

    # Retrieve a class name using the random index.
    selected_class_name = all_classes_names[random_index]

    # Retrieve the list of all the video files present in the randomly selected class directory
    video_files_names_list = os.listdir(f'UCF50/{selected_class_name}')

    # Randomly select a video file from the list retrieved from the randomly selected class Directory.
    selected_video_file_name = random.choice(video_files_names_list)

    # Initialize a VideoCapture object to read from the video file.
    video_reader = cv2.VideoCapture(f'UCF50/{selected_class_name}/{selected_video_file_name}')

    # Read the first frame of the video file.
    _, bgr_frame = video_reader.read()

    # Release the VideoCapture object.
    video_reader.release()

    # Convert the frame from BGR into RGB format.
    rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
