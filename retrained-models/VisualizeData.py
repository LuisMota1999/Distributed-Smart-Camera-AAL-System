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

# Allow us to control the randomness
seed_constant = 27
np.random.seed(seed_constant)
tf.random.set_seed(seed_constant)

# Create a Matplotlib figure and specify the size of the figure
plt.figure(figsize=(20, 20))

# Get the names of all classes/categories in UCF50
all_classes_names = os.listdir('./datasets/UCF50/')

# Generate a list of 20 random values. The values will be between 0-50,
# where 50 is the total number of class in the dataset.
random_range = random.sample(range(len(all_classes_names)), 20)

# Calculate the number of rows and columns for the grid
num_rows = math.ceil(math.sqrt(len(random_range)))
num_cols = math.ceil(len(random_range) / num_rows)

# Create a Matplotlib figure and specify the size of the figure
plt.figure(figsize=(20, 20))

# Iterating through all the generated random values.
for counter, random_index in enumerate(random_range, 1):
    # Retrieve a class name using the random index.
    selected_class_name = all_classes_names[random_index]

    # Retrieve the list of all the video files present in the randomly selected class directory
    video_files_names_list = os.listdir(f'./datasets/UCF50/{selected_class_name}')

    # Randomly select a video file from the list retrieved from the randomly selected class Directory.
    selected_video_file_name = random.choice(video_files_names_list)

    # Initialize a VideoCapture object to read from the video file.
    video_reader = cv2.VideoCapture(f'./datasets/UCF50/{selected_class_name}/{selected_video_file_name}')

    # Read the first frame of the video file.
    _, bgr_frame = video_reader.read()

    # Release the VideoCapture object.
    video_reader.release()

    # Convert the frame from BGR into RGB format.
    rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)

    # Write the class name on the video frame
    cv2.putText(rgb_frame, selected_class_name, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    # Display the frame in the corresponding subplot
    plt.subplot(num_rows, num_cols, counter)
    plt.imshow(rgb_frame)
    plt.axis('off')

# Remove empty subplots if necessary
for i in range(len(random_range) + 1, num_rows * num_cols + 1):
    plt.subplot(num_rows, num_cols, i)
    plt.axis('off')

# Show the plot with all the images
plt.tight_layout()
plt.show()

