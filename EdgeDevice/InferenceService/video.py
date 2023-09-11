import os

from official.projects.movinet.modeling import movinet
from official.projects.movinet.modeling import movinet_model
from official.projects.movinet.tools import export_saved_model
import tensorflow as tf

from RetrainedModels.video.utils.constants import VideoInference

model_id = 'a0'
use_positional_encoding = model_id in {'a3', 'a4', 'a5'}
CLASSES_LABELS = sorted(os.listdir(
    'C:\\Users\luisp\\Desktop\\Distributed-Smart-Camera-AAL-System\RetrainedModels\\video\\datasets\\ToyotaSmartHome\\train'))

# Create the interpreter and signature runner
interpreter = tf.lite.Interpreter(
    model_path='C:\\Users\\luisp\\Desktop\\Distributed-Smart-Camera-AAL-System\\EdgeDevice\\models\\movinet_retrained.tflite')
runner = interpreter.get_signature_runner()

init_states = {
    name: tf.zeros(x['shape'], dtype=x['dtype'])
    for name, x in runner.get_input_details().items()
}
del init_states['image']


def load_gif(file_path, image_size=(224, 224)):
    """Loads a gif file into a TF tensor."""
    with tf.io.gfile.GFile(file_path, 'rb') as f:
        video = tf.io.decode_gif(f.read())
    video = tf.image.resize(video, image_size)
    video = tf.cast(video, tf.float32) / 255.
    return video


def get_top_k(probs, k=5, label_map=CLASSES_LABELS):
    """Outputs the top k model labels and probabilities on the given video."""
    top_predictions = tf.argsort(probs, axis=-1, direction='DESCENDING')[:k]
    top_labels = tf.gather(label_map, top_predictions, axis=-1)
    top_labels = [label.decode('utf8') for label in top_labels.numpy()]
    top_probs = tf.gather(probs, top_predictions, axis=-1).numpy()
    return tuple(zip(top_labels, top_probs))


def predict_top_k(model, video, k=5, label_map=CLASSES_LABELS):
    """Outputs the top k model labels and probabilities on the given video."""
    outputs = model.predict(video[tf.newaxis])[0]
    probs = tf.nn.softmax(outputs)
    return get_top_k(probs, k=k, label_map=label_map)


video = load_gif(
    '/EdgeDevice/models/video_demos/readBookDemo.gif',
    image_size=(172, 172))
clips = tf.split(video[tf.newaxis], video.shape[0], axis=1)

# To run on a video, pass in one frame at a time
states = init_states
for clip in clips:
    # Input shape: [1, 1, 172, 172, 3]
    outputs = runner(**states, image=clip)
    logits = outputs.pop('logits')[0]
    states = outputs

probs = tf.nn.softmax(logits)
top_k = get_top_k(probs)
print()
for label, prob in top_k:
    print(label, prob)
