import collections
import pathlib
import random

import cv2
import matplotlib.pyplot as plt
import numpy as np
import remotezip as rz
import seaborn as sns
import tensorflow as tf
import tqdm
from official.projects.movinet.modeling import movinet
from official.projects.movinet.modeling import movinet_model

URL = 'https://storage.googleapis.com/thumos14_files/UCF101_videos.zip'
download_dir = pathlib.Path('./UCF101_subset/')


def list_files_per_class(zip_url):
    files = []
    with rz.RemoteZip(zip_url) as zip:
        for zip_info in zip.infolist():
            files.append(zip_info.filename)
    return files


def get_class(fname):
    return fname.split('_')[-3]


def get_files_per_class(files):
    files_for_class = collections.defaultdict(list)
    for fname in files:
        class_name = get_class(fname)
        files_for_class[class_name].append(fname)
    return files_for_class


def download_from_zip(zip_url, to_dir, file_names):
    with rz.RemoteZip(zip_url) as zip:
        for fn in tqdm.tqdm(file_names):
            class_name = get_class(fn)
            zip.extract(fn, str(to_dir / class_name))
            unzipped_file = to_dir / class_name / fn

            fn = pathlib.Path(fn).parts[-1]
            output_file = to_dir / class_name / fn
            unzipped_file.rename(output_file)


def split_class_lists(files_for_class, count):
    split_files = []
    remainder = {}
    for cls in files_for_class:
        split_files.extend(files_for_class[cls][:count])
        remainder[cls] = files_for_class[cls][count:]
    return split_files, remainder


def download_ufc_101_subset(zip_url, num_classes, splits, download_dir):
    files = list_files_per_class(zip_url)
    for f in files:
        tokens = f.split('/')
        if len(tokens) <= 2:
            files.remove(f)

    files_for_class = get_files_per_class(files)

    classes = list(files_for_class.keys())[:num_classes]

    for cls in classes:
        new_files_for_class = files_for_class[cls]
        random.shuffle(new_files_for_class)
        files_for_class[cls] = new_files_for_class

    files_for_class = {x: files_for_class[x] for x in list(files_for_class)[:num_classes]}

    dirs = {}
    for split_name, split_count in splits.items():
        print(split_name, ":")
        split_dir = download_dir / split_name
        split_files, files_for_class = split_class_lists(files_for_class, split_count)
        download_from_zip(zip_url, split_dir, split_files)
        dirs[split_name] = split_dir

    return dirs


def format_frames(frame, output_size):
    frame = tf.image.convert_image_dtype(frame, tf.float32)
    frame = tf.image.resize_with_pad(frame, *output_size)
    return frame


def frames_from_video_file(video_path, n_frames, output_size=(224, 224), frame_step=15):
    result = []
    src = cv2.VideoCapture(str(video_path))

    video_length = src.get(cv2.CAP_PROP_FRAME_COUNT)

    need_length = 1 + (n_frames - 1) * frame_step

    if need_length > video_length:
        start = 0
    else:
        max_start = video_length - need_length
        start = random.randint(0, max_start + 1)

    src.set(cv2.CAP_PROP_POS_FRAMES, start)
    ret, frame = src.read()
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = format_frames(frame, output_size)
    result.append(frame)

    while len(result) < n_frames:
        for _ in range(frame_step - 1):
            ret, _ = src.read()
        ret, frame = src.read()
        if not ret:
            break
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = format_frames(frame, output_size)
        result.append(frame)

    while len(result) < n_frames:
        result.append(result[-1])

    src.release()
    return np.stack(result)


def load_movinet(weights_path, num_classes):
    model = movinet_model.MovinetClassifier(
        model_id='a0',
        num_classes=num_classes,
        temporal_size=300,
        temporal_downsample=16,
        norm_mom=0.99,
        norm_epsilon=1e-3,
        kernel_initializer='VarianceScaling'
    )

    dummy_input = tf.keras.Input(shape=(300, 224, 224, 3))
    _ = model(dummy_input)

    model.load_weights(weights_path)

    return model


def predict_video_class(video_path, model, output_size=(224, 224), n_frames=8):
    frames = frames_from_video_file(video_path, n_frames, output_size=output_size)
    frames = np.expand_dims(frames, axis=0)
    predictions = model.predict(frames)
    return predictions


def plot_prediction(predictions, class_names):
    sns.barplot(x=predictions[0], y=class_names)
    plt.show()


def main():
    zip_url = URL
    num_classes = 5
    splits = {'train': 30, 'val': 10, 'test': 10}

    download_dirs = download_ufc_101_subset(zip_url, num_classes, splits, download_dir)

    weights_path = '/path/to/movinet_weights'
    model = load_movinet(weights_path, num_classes)

    class_names = list(download_dirs.keys())

    for split_name, split_dir in download_dirs.items():
        for class_dir in split_dir.iterdir():
            video_files = list(class_dir.glob('*.avi'))
            video_file = random.choice(video_files)
            predictions = predict_video_class(video_file, model)
            plot_prediction(predictions, class_names)


if __name__ == '__main__':
    main()
