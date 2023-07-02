import datetime as dt

import cv2
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from moviepy.editor import *
from sklearn.model_selection import train_test_split

# Allow us to control the randomness
seed_constant = 27
np.random.seed(seed_constant)
tf.random.set_seed(seed_constant)

# Specify the height and width to which each video frame will be resized in our dataset
IMAGE_HEIGHT, IMAGE_WIDTH = 64, 64

# Specify the number of frames of a video that will be fed to the model as one sequence.
SEQUENCE_LENGTH = 20

# Specify the directory containing the UCF50 dataset
DATASET_DIR = "datasets/Charades/"

# Specify the list containing the names of the classes used for training.
CLASSES_LIST = ["Washing_a_window", "Working_at_a_table", "Opening_a_laptop"]


def plot_metrics(model_training_history, metric_name_1, metric_name_2, plot_name):
    """
    This function will display the metrics passed to it in a graph.
    :param model_training_history: A history object containing a record of training and validation loss values
                                and metrics values at successive epochs
    :param metric_name_1: The name of the first metric that needs to be plotted in the graph
    :param metric_name_2: The name of the second metric that needs to be plotted in the graph
    :param plot_name: The title of the graph
    :return:
    """

    # Get metric values using metric names as identifiers.
    metric_value_1 = model_training_history[metric_name_1]
    metric_value_2 = model_training_history[metric_name_2]

    # Construct a range object which will be used as x-axis (horizontal plane) of the graph
    epochs = range(len(metric_value_1))

    # Plot the graph
    plt.plot(epochs, metric_value_1, 'blue', label=metric_name_1)
    plt.plot(epochs, metric_value_2, 'red', label=metric_name_2)

    # Add title to the plot
    plt.title(str(plot_name))

    # Add legend to the plot
    plt.legend()


def frames_extraction(video_path):
    """
    This function will extract the required frames from a video after resizing and normalizing them.
    :param video_path: The path of the video in the disk, whose frames are to be extracted.
    :return frames_list: A list containing the resized and normalized frames of the video.
    """

    # Declare a list to store video frames.
    frames_list = []

    # Read the video file using the VideoCapture object
    video_reader = cv2.VideoCapture(video_path)

    # Get the total number of frames in the video.
    video_frames_count = int(video_reader.get(cv2.CAP_PROP_FRAME_COUNT))

    # Calculate the interval after which frames will be added to the list
    skip_frames_window = max(int(video_frames_count / SEQUENCE_LENGTH), 1)

    # Iterate through the video frames.
    for frame_counter in range(SEQUENCE_LENGTH):

        # Set the current frame position of the video.
        video_reader.set(cv2.CAP_PROP_POS_FRAMES, frame_counter * skip_frames_window)

        # Reading the frame from the video
        success, frame = video_reader.read()

        # Check if video frame is not successfully read then break the loop
        if not success:
            break

        # Resize the frame to fixed height and width.
        resized_frame = cv2.resize(frame, (IMAGE_HEIGHT, IMAGE_WIDTH))

        # Normalize the resized frame by diving it with 255 so that each pixel value then lies between 0 and 1
        normalized_frame = resized_frame / 255

        # Append the normalized frame into the frames list
        frames_list.append(normalized_frame)

    # Release the VideoCapture object
    video_reader.release()

    # Return the frames list
    return frames_list


def create_dataset():
    """
    This function will extract the data of the selected classes and create the required dataset :return features,
    labels, video_files_paths: A list of containing the extracted frames of the videos and the indexes of the classes
    associated with the videos and the paths of the videos in the disk.
    """

    # Declared empty lists to store the features, labels and video file path values.
    features = []
    labels = []
    video_files_paths = []

    # Iterating through all the classes mentioned in the classes list
    for class_index, class_name in enumerate(CLASSES_LIST):
        # Display the name of the class whose data is being extracted:
        print(f'Extracting data of class: {class_name}')

        # Get the list of video files present in the specific class name directory
        files_list = os.listdir(os.path.join(DATASET_DIR, class_name))

        for file_name in files_list:

            # Get the complete video path
            video_files_path = os.path.join(DATASET_DIR, class_name, file_name)

            # Extract the frames of the video file
            frames = frames_extraction(video_files_path)

            # Check if the extracted frames are equal to the SEQUENCE_LENGTH specified above.
            # So ignore the videos having frames less than the SEQUENCE_LENGTH
            if len(frames) == SEQUENCE_LENGTH:
                # Append the data to their respective lists
                features.append(frames)
                labels.append(class_index)
                video_files_paths.append(video_files_path)

    # Converting the list to numpy arrays
    features = np.asarray(features)
    labels = np.array(labels)

    # Return the frames, class index and video file path.
    return features, labels, video_files_paths


# Create the dataset
features, labels, video_files_paths = create_dataset()

# Using Kera's to_categorical method to convert labels into one-hot-encoded vectors
one_hot_encoded_labels = tf.keras.utils.to_categorical(labels)

# Split the data into train (75%) and Test Set (25%)
features_train, features_test, labels_train, labels_test = train_test_split(features, one_hot_encoded_labels,
                                                                            test_size=0.25, shuffle=True,
                                                                            random_state=seed_constant)


def create_convlstm_model():
    """
    This function will construct the required convlstm model.
    :return model: It is the required constructed convlstm model.
    """

    model = tf.keras.Sequential()

    # Define the model architecture
    ##################################################################################################################
    model.add(tf.keras.layers.ConvLSTM2D(filters=4, kernel_size=(3, 3), activation='tanh', data_format="channels_last",
                                         recurrent_dropout=0.2, return_sequences=True,
                                         input_shape=(SEQUENCE_LENGTH, IMAGE_HEIGHT, IMAGE_WIDTH, 3)))

    model.add(tf.keras.layers.MaxPooling3D(pool_size=(1, 2, 2), padding='same', data_format='channels_last'))
    model.add(tf.keras.layers.TimeDistributed(tf.keras.layers.Dropout(0.2)))

    model.add(tf.keras.layers.ConvLSTM2D(filters=8, kernel_size=(3, 3), activation='tanh', data_format="channels_last",
                                         recurrent_dropout=0.2, return_sequences=True))

    model.add(tf.keras.layers.MaxPooling3D(pool_size=(1, 2, 2), padding='same', data_format='channels_last'))
    model.add(tf.keras.layers.TimeDistributed(tf.keras.layers.Dropout(0.2)))

    model.add(tf.keras.layers.ConvLSTM2D(filters=14, kernel_size=(3, 3), activation='tanh', data_format="channels_last",
                                         recurrent_dropout=0.2, return_sequences=True))

    model.add(tf.keras.layers.MaxPooling3D(pool_size=(1, 2, 2), padding='same', data_format='channels_last'))
    model.add(tf.keras.layers.TimeDistributed(tf.keras.layers.Dropout(0.2)))

    model.add(tf.keras.layers.ConvLSTM2D(filters=16, kernel_size=(3, 3), activation='tanh', data_format="channels_last",
                                         recurrent_dropout=0.2, return_sequences=True))

    model.add(tf.keras.layers.MaxPooling3D(pool_size=(1, 2, 2), padding='same', data_format='channels_last'))
    # model.add(tf.keras.layers.TimeDistributed(tf.keras.layers.Dropout(0.2)))
    model.add(tf.keras.layers.Flatten())

    model.add(tf.keras.layers.Dense(len(CLASSES_LIST), activation="softmax"))
    ##################################################################################################################

    # Display the models summary
    model.summary()

    # Return the constructed convlstm model.
    return model


# # Construct the required convelstm model
# convlstm_model = create_convlstm_model()
#
# # Display the success message.
# print("Model created successfully")
#
# # Plot the structure of the constructed model
# tf.keras.utils.plot_model(convlstm_model, to_file='convlstm_model_structure_plot.png', show_shapes=True,
#                           show_layer_names=True)
#
# # Create an Instance of Early Stopping Callback to prevent over fitting
# early_stopping_callback = tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=10, mode='min',
#                                                            restore_best_weights=True)
#
# # Compile the model and specify loss function, optimizer and metrics values to the model
# convlstm_model.compile(loss='categorical_crossentropy', optimizer='Adam', metrics=['accuracy'])
#
# # Start training the model
# convlstm_model_training_history = convlstm_model.fit(x=features_train, y=labels_train, epochs=50, batch_size=4,
#                                                      shuffle=True, validation_split=0.2,
#                                                      callbacks=[early_stopping_callback])
#
# # Evaluate the trained model
# model_evaluation_history = convlstm_model.evaluate(features_test, labels_test)
#
# # Get the loss and accuracy from model_evaluation_history
# model_evaluation_loss, model_evaluation_accuracy = model_evaluation_history
#
# # Define the string date format
# # Get the current Date and Time in a DateTime Object.
# # Convert the DateTime object to string according to the style mentioned in date_time_format string
# date_time_format = '%Y_%m_%d__%H_%M_%S'
# current_date_time_dt = dt.datetime.now()
# current_date_time_string = dt.datetime.strftime(current_date_time_dt, date_time_format)
#
# # Define the name for retrained model
# model_file_name = f'convlstm_model__Date_time_{current_date_time_string}__Loss_{model_evaluation_loss}__Accuracy_{model_evaluation_accuracy}.h5'
#
# # Save model
# convlstm_model.save(model_file_name)


# # Visualize the training and validation loss metrics.
# plot_metrics(convlstm_model_training_history, 'loss', 'val_loss', 'Total Loss Vs Total Validation Loss')
#
# # Visualize the training and validation accuracy metrics
# plot_metrics(convlstm_model_training_history, 'accuracy', 'val_accuracy', 'Total Accuracy Vs Total Validation Accuracy')


def create_LRCN_model():
    """
    This function will construct the required LRCN model.
    :return model: It is the required constructed LRCN model.
    """
    model = tf.keras.Sequential()

    # Define the model architecture
    ##################################################################################################################
    model.add(tf.keras.layers.TimeDistributed(tf.keras.layers.Conv2D(16, (3, 3), padding='same', activation='relu'),
                                              input_shape=(SEQUENCE_LENGTH, IMAGE_HEIGHT, IMAGE_WIDTH, 3)))
    model.add(tf.keras.layers.TimeDistributed(tf.keras.layers.BatchNormalization()))
    model.add(tf.keras.layers.TimeDistributed(tf.keras.layers.MaxPooling2D((4, 4))))
    model.add(tf.keras.layers.TimeDistributed(tf.keras.layers.Dropout(0.25)))

    model.add(tf.keras.layers.TimeDistributed(tf.keras.layers.Conv2D(32, (3, 3), padding='same', activation='relu')))
    model.add(tf.keras.layers.TimeDistributed(tf.keras.layers.BatchNormalization()))
    model.add(tf.keras.layers.TimeDistributed(tf.keras.layers.MaxPooling2D((4, 4))))
    model.add(tf.keras.layers.TimeDistributed(tf.keras.layers.Dropout(0.25)))

    model.add(tf.keras.layers.TimeDistributed(tf.keras.layers.Conv2D(64, (3, 3), padding='same', activation='relu')))
    model.add(tf.keras.layers.TimeDistributed(tf.keras.layers.BatchNormalization()))
    model.add(tf.keras.layers.TimeDistributed(tf.keras.layers.MaxPooling2D((2, 2))))
    model.add(tf.keras.layers.TimeDistributed(tf.keras.layers.Dropout(0.25)))

    model.add(tf.keras.layers.TimeDistributed(tf.keras.layers.Conv2D(64, (3, 3), padding='same', activation='relu')))
    model.add(tf.keras.layers.TimeDistributed(tf.keras.layers.BatchNormalization()))
    model.add(tf.keras.layers.TimeDistributed(tf.keras.layers.MaxPooling2D((2, 2))))
    model.add(tf.keras.layers.TimeDistributed(tf.keras.layers.Flatten()))

    model.add(tf.keras.layers.LSTM(32, return_sequences=True))
    model.add(tf.keras.layers.LSTM(32))
    model.add(tf.keras.layers.Dense(len(CLASSES_LIST), activation="softmax"))
    ##################################################################################################################

    # Display the model's summary
    model.summary()

    return model


# Construct the required LRCN model.
LRCN_model = create_LRCN_model()

# Display the success message
print("LRCN Model created successfully!")

# Plot the structure of the constructed model
tf.keras.utils.plot_model(LRCN_model, to_file='../assets/model_video_imgs/LRCN_model_structure_plot.png', show_shapes=True,
                          show_layer_names=True)

# Create an Instance of Early Stopping Callback to prevent over fitting
early_stopping_callback = tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=15, mode='min',
                                                           restore_best_weights=True)

# Compile the model and specify loss function, optimizer and metrics values to the model
LRCN_model.compile(loss='categorical_crossentropy', optimizer='Adam', metrics=['accuracy'])

# Start training the model
LRCN_model_training_history = LRCN_model.fit(x=features_train, y=labels_train, epochs=70, batch_size=4,
                                             shuffle=True, validation_split=0.2,
                                             callbacks=[early_stopping_callback])

# Evaluate the trained model
model_evaluation_history = LRCN_model.evaluate(features_test, labels_test)
print("Model evaluation ", model_evaluation_history)

# Get the loss and accuracy from model_evaluation_history
model_evaluation_loss, model_evaluation_accuracy = model_evaluation_history

# Define the string date format
# Get the current Date and Time in a DateTime Object.
# Convert the DateTime object to string according to the style mentioned in date_time_format string
date_time_format = '%Y_%m_%d__%H_%M_%S'
current_date_time_dt = dt.datetime.now()
current_date_time_string = dt.datetime.strftime(current_date_time_dt, date_time_format)

# Define the name for retrained model
model_file_name = f'LRCN_model__Date_time_{current_date_time_string}__Loss_{model_evaluation_loss}__Accuracy_{model_evaluation_accuracy}.h5'

# Save model
LRCN_model.save(model_file_name)

# Visualize the training and validation loss metrics.
plot_metrics(LRCN_model_training_history, 'loss', 'val_loss', 'Total Loss Vs Total Validation Loss')

# Visualize the training and validation accuracy metrics
plot_metrics(LRCN_model_training_history, 'accuracy', 'val_accuracy', 'Total Accuracy Vs Total Validation Accuracy')
