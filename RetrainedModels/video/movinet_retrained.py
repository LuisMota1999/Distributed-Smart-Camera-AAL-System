import os
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import tensorflow as tf
from official.projects.movinet.modeling import movinet
from official.projects.movinet.modeling import movinet_model
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from RetrainedModels.video.utils.constants import VideoInference
from RetrainedModels.video.filters.DataExtraction import FrameGenerator, ToyotaSmartHomeDataset
from official.projects.movinet.tools import export_saved_model

# Define constants and paths
CLASSES_LABEL = sorted(os.listdir(VideoInference.DATASET_DIRECTORY.value + 'train'))
MODEL_ID = 'a0'
USE_POSITIONAL_ENCODING = MODEL_ID in {'a3', 'a4', 'a5'}
RESOLUTION = 172
CHECKPOINT_DIR = "movinet_a0_stream"
CHECKPOINT_DIR_OUTPUT = 'trained_model'
CHECKPOINT_PATH = tf.train.latest_checkpoint(CHECKPOINT_DIR)
SAVED_MODEL_DIR = 'model'
TFLITE_FILENAME = '../../EdgeDevice/models/movinet_retrained.tflite'
INPUT_SHAPE = [1, VideoInference.NUM_FRAMES.value, RESOLUTION, RESOLUTION, 3]
DATASET_TOYOTASMARTHOME = ToyotaSmartHomeDataset(VideoInference.DATASET_DIRECTORY.value + 'mp4',
                                                 VideoInference.DATASET_DIRECTORY.value)
SUBSET_PATHS = DATASET_TOYOTASMARTHOME.dirs

OUTPUT_SIGNATURE = (tf.TensorSpec(shape=(None, None, None, 3), dtype=tf.float32),
                    tf.TensorSpec(shape=(), dtype=tf.int16))


# Load data for the train, validation, and test sets
def load_dataset(subset_dataset, subset_size, training=True):
    """
    Load video frame data from a dataset directory and create a TensorFlow Dataset.

    Args:
        subset_dataset (str): Path to the dataset directory.
        subset_size (int): Number of samples to load from the dataset.
        training (bool): Whether to load data for training.

    Returns:
        tf.data.Dataset: A TensorFlow Dataset containing video frame data and labels.
    """
    generator = FrameGenerator(subset_dataset, n_frames=VideoInference.NUM_FRAMES.value,
                               dataset=DATASET_TOYOTASMARTHOME,
                               subset_size=subset_size, training=training)
    dataset = tf.data.Dataset.from_generator(generator, output_signature=OUTPUT_SIGNATURE)
    return dataset.batch(VideoInference.BATCH_SIZE.value)


# Load train, validation, and test datasets
train_ds = load_dataset(SUBSET_PATHS['train'], VideoInference.TRAIN_SUBSET_SIZE.value, training=True)
val_ds = load_dataset(SUBSET_PATHS['val'], VideoInference.VAL_SUBSET_SIZE.value, training=False)
test_ds = load_dataset(SUBSET_PATHS['test'], VideoInference.TEST_SUBSET_SIZE.value, training=False)

# Print shape of a batch from the train dataset
for frames, labels in train_ds.take(1):
    print(f"Shape: {frames.shape}")
    print(f"Label: {labels.shape}")

# Create Movinet backbone
backbone = movinet.Movinet(
    model_id=MODEL_ID,
    causal=True,
    conv_type='2plus1d',
    se_type='2plus3d',
    activation='hard_swish',
    gating_activation='hard_sigmoid',
    use_positional_encoding=USE_POSITIONAL_ENCODING,
    use_external_states=False,
)

# Create a temporary model to load a pre-trained checkpoint
model = movinet_model.MovinetClassifier(
    backbone,
    num_classes=600,
    output_states=True)

# Load Pretrained checkpoint
inputs = tf.ones([1, 13, 172, 172, 3])

# Build the model and load a pretrained checkpoint.
model.build(inputs.shape)

CHECKPOINT = tf.compat.v2.train.Checkpoint(model=model)
status = CHECKPOINT.restore(CHECKPOINT_PATH).expect_partial()
if status is None:
    raise ValueError("Checkpoint loading failed. Checkpoint status is None.")

# Distribution strategy setup
try:
    tpu_resolver = tf.distribute.cluster_resolver.TPUClusterResolver()  # TPU detection
except ValueError:
    tpu_resolver = None
    gpus = tf.config.experimental.list_logical_devices("GPU")

if tpu_resolver:
    tf.config.experimental_connect_to_cluster(tpu_resolver)
    tf.tpu.experimental.initialize_tpu_system(tpu_resolver)
    distribution_strategy = tf.distribute.experimental.TPUStrategy(tpu_resolver)
    print('Running on TPU ', tpu_resolver.cluster_spec().as_dict()['worker'])
elif len(gpus) > 1:
    distribution_strategy = tf.distribute.MirroredStrategy([gpu.name for gpu in gpus])
    print('Running on multiple GPUs ', [gpu.name for gpu in gpus])
elif len(gpus) == 1:
    distribution_strategy = tf.distribute.get_strategy()  # default strategy that works on CPU and single GPU
    print('Running on single GPU ', gpus[0].name)
else:
    distribution_strategy = tf.distribute.get_strategy()  # default strategy that works on CPU and single GPU
    print('Running on CPU')

print("Number of accelerators: ", distribution_strategy.num_replicas_in_sync)


# Define a function to build the classifier model
def build_classifier(batch_size, num_frames, resolution, backbone, num_classes):
    """
    Build a Movinet-based classifier model.

    Args:
        batch_size (int): Batch size for the model.
        num_frames (int): Number of frames in a video.
        resolution (int): Resolution of video frames.
        backbone (tf.keras.Model): Movinet backbone model.
        num_classes (int): Number of classes for classification.

    Returns:
        tf.keras.Model: A classifier model.
    """
    model = movinet_model.MovinetClassifier(
        backbone=backbone,
        num_classes=num_classes)
    model.build([batch_size, num_frames, resolution, resolution, 3])
    return model


# Define a function to plot accuracy and loss
def plot_accuracy_loss(history):
    """
    Plot the accuracy and loss of a model during training.

    Args:
        history (tf.keras.callbacks.History): History object from model training.
    """
    plt.plot(history.history['accuracy'])
    plt.plot(history.history['loss'])
    plt.title('Model Accuracy - Loss (Video)')
    plt.ylabel(' ')
    plt.xlabel('epoch')
    plt.xlim([0, VideoInference.NUM_EPOCHS.value])
    plt.legend(['accuracy', 'loss'], loc='best')
    plt.show()


# Define a function to plot a confusion matrix
def plot_confusion_matrix(actual, predicted, labels, ds_type):
    """
    Plot a confusion matrix for classification results.

    Args:
        actual (tf.Tensor): Ground truth labels.
        predicted (tf.Tensor): Predicted labels.
        labels (list): List of class labels.
        ds_type (str): Type of dataset (e.g., 'train', 'validation', 'test').
    """
    cm = tf.math.confusion_matrix(actual, predicted)
    ax = sns.heatmap(cm, annot=True, fmt='g')
    sns.set(rc={'figure.figsize': (12, 12)})  # Adjust the figure size as needed
    sns.set(font_scale=1.2)
    ax.set_title('Confusion matrix of action recognition for ' + ds_type)
    ax.set_xlabel('Predicted Action')
    ax.set_ylabel('Actual Action')
    plt.xticks(rotation=90)
    plt.yticks(rotation=0)

    # Ensure the number of labels matches the number of tick locations
    ax.xaxis.set_ticklabels(labels, rotation=90)
    ax.yaxis.set_ticklabels(labels, rotation=0)

    plt.show()


# Define a function to get actual and predicted labels
def get_actual_predicted_labels(dataset):
    """
    Create a list of actual ground truth values and the predictions from the model.

    Args:
        dataset: An iterable data structure, such as a TensorFlow Dataset, with features and labels.

    Return:
        Ground truth and predicted values for a particular dataset.
    """
    actual = [labels for _, labels in dataset.unbatch()]
    predicted = model.predict(dataset)

    actual = tf.stack(actual, axis=0)
    predicted = tf.concat(predicted, axis=0)
    predicted = tf.argmax(predicted, axis=1)

    return actual, predicted


# Define a function to convert the model to TFLite format
def convert_model_to_tflite(saved_model_dir, input_model_shape, model_filename_ouput_directory):
    """
    Convert a TensorFlow SavedModel to TFLite format.

    Args:
        saved_model_dir (str): Directory where the SavedModel is saved.
        input_model_shape (list): Shape of the input model.
        model_filename_ouput_directory (str): Output directory for the TFLite model file.
    """
    export_saved_model.export_saved_model(
        model=model,
        input_shape=input_model_shape,
        export_path=saved_model_dir,
        causal=True,
        bundle_input_init_states_fn=False)

    converter = tf.lite.TFLiteConverter.from_saved_model(saved_model_dir)
    tflite_model = converter.convert()

    with open(model_filename_ouput_directory, 'wb') as f:
        f.write(tflite_model)


# Training and evaluation
with distribution_strategy.scope():
    model = build_classifier(VideoInference.BATCH_SIZE.value, VideoInference.NUM_FRAMES.value, RESOLUTION, backbone,
                             VideoInference.NUM_CLASSES.value)
    loss_obj = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
    optimizer = tf.keras.optimizers.Adam(learning_rate=0.001)
    model.compile(loss=loss_obj, optimizer=optimizer, metrics=['accuracy'])

cp_callback = tf.keras.callbacks.ModelCheckpoint(filepath=CHECKPOINT_DIR_OUTPUT, save_weights_only=True, verbose=1)

results = model.fit(train_ds, validation_data=val_ds, epochs=VideoInference.NUM_EPOCHS.value, validation_freq=1,
                    verbose=1, callbacks=[cp_callback])

model.evaluate(test_ds)

plot_accuracy_loss(results)

fg = FrameGenerator(SUBSET_PATHS['train'], VideoInference.NUM_FRAMES.value, dataset=DATASET_TOYOTASMARTHOME,
                    training=True)
label_names = list(fg.class_ids_for_name.keys())

actual, predicted = get_actual_predicted_labels(test_ds)
plot_confusion_matrix(actual, predicted, label_names, 'test')

accuracy = accuracy_score(actual, predicted)
precision = precision_score(actual, predicted, average='weighted')
recall = recall_score(actual, predicted, average='weighted')
f1 = f1_score(actual, predicted, average='weighted', labels=np.unique(predicted))

print(f"Accuracy: {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall: {recall:.4f}")
print(f"F1-score: {f1:.4f}")
