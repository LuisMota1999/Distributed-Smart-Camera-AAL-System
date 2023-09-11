# Import libraries
import pathlib

import matplotlib as mpl
import matplotlib.pyplot as plt
import mediapy as media
import numpy as np
from PIL import Image

import tensorflow as tf
import tqdm

mpl.rcParams.update({
    'font.size': 10,
})

labels_path = 'C:\\Users\\LPMOTA\\Desktop\\Distributed-Smart-Camera-AAL-System\\EdgeDevice\\models\\movinet_labels.txt'
labels_path = pathlib.Path(labels_path)

lines = labels_path.read_text().splitlines()
KINETICS_600_LABELS = np.array([line.strip() for line in lines])

print(KINETICS_600_LABELS)

cleanWindows_url = 'https://odditymall.com/includes/content/the-glider-a-magnetic-window-cleaner-that-cleans-both-sides-of-the-glass-0.gif'
cleanWindows_path = tf.keras.utils.get_file(
    fname='readingBook.gif',
    origin=cleanWindows_url,
    cache_dir='.', cache_subdir='.',
)


# @title
# Read and process a video
def load_gif(file_path, image_size=(224, 224)):
    """Loads a gif file into a TF tensor.

    Use images resized to match what's expected by your model.
    The model pages say the "A2" models expect 224 x 224 images at 5 fps

    Args:
      file_path: path to the location of a gif file.
      image_size: a tuple of target size.

    Returns:
      a video of the gif file
    """
    # Load a gif file, convert it to a TF tensor
    raw = tf.io.read_file(file_path)
    video = tf.io.decode_gif(raw)
    # Resize the video
    video = tf.image.resize(video, image_size)
    # change dtype to a float32
    # Hub models always want images normalized to [0,1]
    # ref: https://www.tensorflow.org/hub/common_signatures/images#input
    video = tf.cast(video, tf.float32) / 255.
    return video


readingBook = load_gif(cleanWindows_path)
print(readingBook.shape)

interpreter = tf.lite.Interpreter(
    model_path='C:\\Users\\LPMOTA\Desktop\\Distributed-Smart-Camera-AAL-System\\EdgeDevice\\models\\movinet_a2_stream_k600_int8.tflite')

runner = interpreter.get_signature_runner()
input_details = runner.get_input_details()

print(input_details)


# @title
# Get top_k labels and probabilities
def get_top_k(probs, k=15, label_map=KINETICS_600_LABELS):
    """Outputs the top k model labels and probabilities on the given video.

    Args:
      probs: probability tensor of shape (num_frames, num_classes) that represents
        the probability of each class on each frame.
      k: the number of top predictions to select.
      label_map: a list of labels to map logit indices to label strings.

    Returns:
      a tuple of the top-k labels and probabilities.
    """
    # Sort predictions to find top_k


    top_predictions = tf.argsort(probs, axis=-1, direction='DESCENDING')[:k]
    # collect the labels of top_k predictions
    top_labels = tf.gather(label_map, top_predictions, axis=-1)
    # decode lablels
    print(top_labels)
    top_labels = [label.decode('utf8') for label in top_labels.numpy()]
    # top_k probabilities of the predictions
    top_probs = tf.gather(probs, top_predictions, axis=-1).numpy()
    return tuple(zip(top_labels, top_probs))


def quantized_scale(name, state):
    """Scales the named state tensor input for the quantized model."""
    dtype = input_details[name]['dtype']
    scale, zero_point = input_details[name]['quantization']
    if 'frame_count' in name or dtype == np.float32 or scale == 0.0:
        return state
    return np.cast((state / scale + zero_point), dtype)


# Create the initial states, scale quantized.
init_states = {
    name: quantized_scale(name, np.zeros(x['shape'], dtype=x['dtype']))
    for name, x in input_details.items()
    if name != 'image'
}

print(list(sorted(init_states.keys()))[:5])

inputs = init_states.copy()

inputs['image'] = readingBook[tf.newaxis, 0:1, ...]

states = init_states

video = readingBook
images = tf.split(video[tf.newaxis], video.shape[0], axis=1)

print(images)
all_logits = []

for frame in tqdm.tqdm(images):
    # Normally the input frame is normalized to [0, 1] with dtype float32, but
    # here we apply quantized scaling to fit values into the quantized dtype.
    frame = quantized_scale('image', frame)
    # Input shape: [1, 1, 224, 224, 3]
    outputs = runner(**states, image=frame)
    # `logits` will output predictions on each frame.
    logits = outputs.pop('logits')
    all_logits.append(logits)

# concatinating all the logits
logits = tf.concat(all_logits, 0)
# estimating probabilities
probs = tf.nn.softmax(logits, axis=-1)

final_probs = probs[-1]
print(final_probs)
print('Top_k predictions and their probablities\n')
for label, p in get_top_k(final_probs):
    print(f'{label:20s}: {p:.3f}')
