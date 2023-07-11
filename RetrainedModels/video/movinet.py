# Import libraries
import pathlib

import matplotlib as mpl
import matplotlib.pyplot as plt
import mediapy as media
import numpy as np
import PIL

import tensorflow as tf
import tensorflow_hub as hub
import tqdm

mpl.rcParams.update({
    'font.size': 10,
})

labels_path = tf.keras.utils.get_file(
    fname='labels.txt',
    origin='https://raw.githubusercontent.com/tensorflow/models/f8af2291cced43fc9f1d9b41ddbf772ae7b0d7d2/official/projects/movinet/files/kinetics_600_labels.txt'
)
labels_path = pathlib.Path(labels_path)

lines = labels_path.read_text().splitlines()
KINETICS_600_LABELS = np.array([line.strip() for line in lines])
selected_classes = ['watching tv']
KINETICS_600_LABELS = KINETICS_600_LABELS[np.isin(KINETICS_600_LABELS, selected_classes)].tolist()

jumpingjack_url = 'https://media.tenor.com/bkdEZtNUnvAAAAAd/watching-tv-serious.gif'
jumpingjack_path = tf.keras.utils.get_file(
    fname='watching-tv-serious.gif',
    origin=jumpingjack_url,
    cache_dir='.', cache_subdir='.',
)

print(KINETICS_600_LABELS)

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


jumpingjack = load_gif(jumpingjack_path)

id = 'a2'
mode = 'base'
version = '3'
hub_url = f'https://tfhub.dev/tensorflow/movinet/{id}/{mode}/kinetics-600/classification/{version}'
model = hub.load(hub_url)

sig = model.signatures['serving_default']
print(sig.pretty_printed_signature())

# warmup
sig(image=jumpingjack[tf.newaxis, :1])

logits = sig(image=jumpingjack[tf.newaxis, ...])
logits = logits['classifier_head'][0]

print(logits.shape)
print()


def get_top_k(probs, k=5, label_map=KINETICS_600_LABELS):
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
    top_labels = [label.decode('utf8') for label in top_labels.numpy()]
    # top_k probabilities of the predictions
    top_probs = tf.gather(probs, top_predictions, axis=-1).numpy()
    return tuple(zip(top_labels, top_probs))


probs = tf.nn.softmax(logits, axis=-1)
for label, p in get_top_k(probs):
    print(f'{label:20s}: {p:.3f}')
