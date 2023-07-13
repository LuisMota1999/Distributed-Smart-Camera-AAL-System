# Import the MoViNet model from TensorFlow Models (tf-models-official) for the MoViNet model
import seaborn as sns
import matplotlib.pyplot as plt
import pathlib
import numpy as np
# Import the MoViNet model from TensorFlow Models (tf-models-official) for the MoViNet model
import tensorflow as tf
from RetrainedModels.video.DataExtraction import UCF101Dataset, FrameGenerator, ToyotaSmartHomeDataset
# Import the MoViNet model from TensorFlow Models (tf-models-official) for the MoViNet model
from official.projects.movinet.modeling import movinet
from official.projects.movinet.modeling import movinet_model

# url_ucf101_dataset = "https://storage.googleapis.com/thumos14_files/UCF101_videos.zip"
# ucf101_output_directory = pathlib.Path('datasets/UCF101/')
# ucf101_classes = ["CuttingInKitchen", "BlowDryHair", "ApplyLipstick"]
# ucf101_dataset = UCF101Dataset(url_ucf101_dataset, ucf101_output_directory, ucf101_classes)

toyota_video_directory = pathlib.Path('datasets/ToyotaSmartHome/mp4/')
toyota_output_directory = pathlib.Path('datasets/ToyotaSmartHome/')

toyotaSmartHome_dataset = ToyotaSmartHomeDataset(toyota_video_directory, toyota_output_directory)

dataset = toyotaSmartHome_dataset
subset_paths = toyotaSmartHome_dataset.dirs
batch_size = 64
num_frames = 8

output_signature = (tf.TensorSpec(shape=(None, None, None, 3), dtype=tf.float32),
                    tf.TensorSpec(shape=(), dtype=tf.int16))

print(output_signature)
train_ds = tf.data.Dataset.from_generator(
    FrameGenerator(subset_paths['train'], n_frames=num_frames, dataset=dataset, training=True),
    output_signature=output_signature)
train_ds = train_ds.batch(batch_size)

test_ds = tf.data.Dataset.from_generator(
    FrameGenerator(path=subset_paths['test'], n_frames=num_frames, dataset=dataset),
    output_signature=output_signature)
test_ds = test_ds.batch(batch_size)

val_ds = tf.data.Dataset.from_generator(
    FrameGenerator(path=subset_paths['val'], n_frames=num_frames, dataset=dataset),
    output_signature=output_signature)
val_ds = val_ds.batch(batch_size)

for frames, labels in train_ds.take(10):
    print(labels)
    print(f"Shape: {frames.shape}")
    print(f"Label: {labels.shape}")

gru = tf.keras.layers.GRU(units=4, return_sequences=True, return_state=True)

inputs = tf.random.normal(shape=[1, 10, 8])  # (batch, sequence, channels)

result, state = gru(inputs)  # Run it all at once

first_half, state = gru(inputs[:, :5, :])  # run the first half, and capture the state
second_half, _ = gru(inputs[:, 5:, :], initial_state=state)  # Use the state to continue where you left off.

print(np.allclose(result[:, :5, :], first_half))
print(np.allclose(result[:, 5:, :], second_half))

model_id = 'a0'
resolution = 172

tf.keras.backend.clear_session()

backbone = movinet.Movinet(model_id=model_id)
backbone.trainable = False

# Set num_classes=600 to load the pre-trained weights from the original model
model = movinet_model.MovinetClassifier(backbone=backbone, num_classes=600)
model.build([None, None, None, None, 3])

checkpoint_dir = pathlib.Path("movinet_a0_base")
checkpoint_path = tf.train.latest_checkpoint(checkpoint_dir)
checkpoint = tf.train.Checkpoint(model=model)
status = checkpoint.restore(checkpoint_path)
status.assert_existing_objects_matched()


def build_classifier(batch_size, num_frames, resolution, backbone, num_classes):
    """Builds a classifier on top of a backbone model."""
    model = movinet_model.MovinetClassifier(
        backbone=backbone,
        num_classes=num_classes)
    model.build([batch_size, num_frames, resolution, resolution, 3])

    return model


model = build_classifier(batch_size, num_frames, resolution, backbone, 64)

num_epochs = 5

loss_obj = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)

optimizer = tf.keras.optimizers.Adam(learning_rate=0.001)

model.compile(loss=loss_obj, optimizer=optimizer, metrics=['accuracy'])

results = model.fit(train_ds,
                    validation_data=test_ds,
                    epochs=num_epochs,
                    validation_freq=1,
                    verbose=1)

model.evaluate(test_ds, return_dict=True)


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


def plot_confusion_matrix(actual, predicted, labels, ds_type):
    print("MATRIX")
    cm = tf.math.confusion_matrix(actual, predicted)
    ax = sns.heatmap(cm, annot=True, fmt='g')
    sns.set(rc={'figure.figsize': (22, 22)})
    sns.set(font_scale=1.4)
    ax.set_title('Matriz de confusão de atividades')
    ax.set_xlabel('Predicted Action')
    ax.set_ylabel('Actual Action')
    plt.xticks(rotation=90)
    plt.yticks(rotation=0)
    ax.xaxis.set_ticklabels(labels)
    ax.yaxis.set_ticklabels(labels)


fg = FrameGenerator(path=subset_paths['train'], n_frames=num_frames, dataset=dataset, training=True)
label_names = list(fg.class_ids_for_name.keys())
actual, predicted = get_actual_predicted_labels(test_ds)
plot_confusion_matrix(actual, predicted, label_names, 'test')
plt.show()
