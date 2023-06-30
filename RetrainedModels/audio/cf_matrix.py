import argparse
import csv
import itertools
import numpy as np

from tflite_runtime.interpreter import Interpreter
import tensorflow as tf
import tensorflow_io as tfio
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--dataset', dest='datasets_path',
                    default='./datasets/', help='Invalid path to datasets!')
args = parser.parse_args()
DATASETS_PATH = args.datasets_path

interpreter = Interpreter(f'../edge_device/models/yamnet_retrained.tflite')
inputs = interpreter.get_input_details()
outputs = interpreter.get_output_details()
waveform_input_index = inputs[0]['index']
scores_output_index = outputs[0]['index']


def read_classes(file):
    classes_read = []
    with open(file, newline='') as f:
        reader = csv.reader(f)
        iterator = iter(reader)
        next(iterator)
        for row in iterator:
            classes_read.append(row[0])
    return classes_read


def load_wav_16k_mono(filename):
    """ read in a waveform file and convert to 16 kHz mono """
    file_contents = tf.io.read_file(filename)
    wav, sample_rate = tf.audio.decode_wav(file_contents, desired_channels=1)
    wav = tf.squeeze(wav, axis=-1)
    sample_rate = tf.cast(sample_rate, dtype=tf.int64)
    wav = tfio.audio.resample(wav, rate_in=sample_rate, rate_out=16000)
    return wav


def runModelonValidation(dataset_path):
    expected = []
    predicted = []

    with open(dataset_path + '/mappings.csv', newline='') as f:
        reader = csv.reader(f)
        iterator = iter(reader)
        next(iterator)
        for row in iterator:
            # print(row)
            if row[1] != "3": continue  # check run only on validation set

            audio_file = dataset_path + '/audio/' + row[0]
            waveform = load_wav_16k_mono(audio_file)
            interpreter.resize_tensor_input(waveform_input_index, [len(waveform)], strict=True)
            interpreter.allocate_tensors()
            interpreter.set_tensor(waveform_input_index, waveform)
            interpreter.invoke()
            scores = interpreter.get_tensor(scores_output_index)
            class_probabilities = np.exp(scores) / np.sum(np.exp(scores), axis=-1)
            top_class = np.argmax(class_probabilities)

            expected.append(int(row[2]))
            predicted.append(top_class)

    return expected, predicted


def plot_confusion_matrix(cm, class_names):
    """
    Returns a matplotlib figure containing the plotted confusion matrix.

    Args:
      cm (array, shape = [n, n]): a confusion matrix of integer classes
      class_names (array, shape = [n]): String names of the integer classes
    """
    figure = plt.figure(figsize=(8, 8))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title("Confusion Matrix")
    plt.colorbar()
    tick_marks = np.arange(len(class_names))
    plt.xticks(tick_marks, class_names, rotation=45)
    plt.yticks(tick_marks, class_names)

    # Compute the labels from the normalized confusion matrix.
    labels = np.around(cm.astype('float') / cm.sum(axis=1)[:, np.newaxis], decimals=2)

    # Use white text if squares are dark; otherwise black.
    threshold = cm.max() / 2.
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        color = "white" if cm[i, j] > threshold else "black"
        plt.text(j, i, labels[i, j], horizontalalignment="center", color=color)

    plt.tight_layout()
    plt.ylabel('True label')
    plt.xlabel('Predicted label')

    figure.show()
    figure.savefig('../assets/model_audio_imgs/confusion_matrix.png')
    return figure


class_names = read_classes('classes_to_retrain.csv')
expected, predicted = runModelonValidation(DATASETS_PATH + 'GENERATED-SOUNDS')
confusion_matrix = tf.math.confusion_matrix(expected, predicted)
figure = plot_confusion_matrix(confusion_matrix.numpy(), class_names)


