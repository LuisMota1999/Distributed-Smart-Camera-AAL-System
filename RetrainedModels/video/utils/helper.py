import os
import cv2
import glob
import shutil
import random
import pathlib


def get_directory_lengths(directory):
    directory_lengths = {}
    for root, dirs, files in os.walk(directory):
        if root != directory:
            directory_lengths[root] = len(files)

    max_dir_length = max(len(dir_name) for dir_name in directory_lengths.keys())
    max_len_length = max(len(str(dir_length)) for dir_length in directory_lengths.values())

    for dir_name, dir_length in directory_lengths.items():
        formatted_dir_name = dir_name.ljust(max_dir_length)
        formatted_dir_length = str(dir_length).ljust(max_len_length)
        print(f"Directory: {formatted_dir_name}\t\tLength: {formatted_dir_length}")


def convert_mp4_to_avi_recursive(root_folder):
    # Traverse through all subdirectories in the root folder
    for root, dirs, files in os.walk(root_folder):
        for mp4_file in glob.glob(os.path.join(root, '*.mp4')):
            # Construct the output AVI file path
            avi_file = os.path.splitext(mp4_file)[0] + '.avi'

            # Read the MP4 file
            video = cv2.VideoCapture(mp4_file)

            # Get video properties
            width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = video.get(cv2.CAP_PROP_FPS)

            # Create the output video writer
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            video_writer = cv2.VideoWriter(avi_file, fourcc, fps, (width, height))

            # Read and write each frame
            while True:
                ret, frame = video.read()
                if not ret:
                    break
                video_writer.write(frame)

            # Release the video reader and writer
            video.release()
            video_writer.release()

            # Delete the original MP4 file
            os.remove(mp4_file)

            # Rename the AVI file to the original MP4 file name
            os.rename(avi_file, mp4_file)

            print(f"Converted {mp4_file} to {avi_file} and replaced the original file")


def split_dataset(root_folder, train_ratio, test_ratio, datasetName):
    # Create the output directories for train, test, and val
    output_folder = os.path.join('Datasets_filtered',datasetName)
    train_dir = os.path.join(output_folder, 'train')
    test_dir = os.path.join(output_folder, 'test')
    val_dir = os.path.join(output_folder, 'val')
    os.makedirs(train_dir, exist_ok=True)
    os.makedirs(test_dir, exist_ok=True)
    os.makedirs(val_dir, exist_ok=True)

    classes = os.listdir(root_folder)
    for class_name in classes:
        class_folder = os.path.join(root_folder, class_name)
        if not os.path.isdir(class_folder):
            continue

        class_files = os.listdir(class_folder)
        random.shuffle(class_files)

        num_files = len(class_files)
        num_train = int(num_files * train_ratio)
        num_test = int(num_files * test_ratio)
        num_val = num_files - num_train - num_test

        train_files = class_files[:num_train]
        test_files = class_files[num_train:num_train + num_test]
        val_files = class_files[num_train + num_test:]

        class_train_dir = os.path.join(train_dir, class_name)
        class_test_dir = os.path.join(test_dir, class_name)
        class_val_dir = os.path.join(val_dir, class_name)
        os.makedirs(class_train_dir, exist_ok=True)
        os.makedirs(class_test_dir, exist_ok=True)
        os.makedirs(class_val_dir, exist_ok=True)

        for file in train_files:
            src = os.path.join(class_folder, file)
            dst = os.path.join(class_train_dir, file)
            try:
                shutil.move(src, dst)
            except PermissionError as e:
                print(f"Permission denied: {e}")

        for file in test_files:
            src = os.path.join(class_folder, file)
            dst = os.path.join(class_test_dir, file)
            try:
                shutil.move(src, dst)
            except PermissionError as e:
                print(f"Permission denied: {e}")

        for file in val_files:
            src = os.path.join(class_folder, file)
            dst = os.path.join(class_val_dir, file)
            try:
                shutil.move(src, dst)
            except PermissionError as e:
                print(f"Permission denied: {e}")

        print(f"Split dataset for class {class_name}:")
        print(f"  train: {num_train} files")
        print(f"  Test: {num_test} files")
        print(f"  Val: {num_val} files")


# Example usage
root_folder = pathlib.Path('C:\\Users\\luisp\Desktop\\Distributed-Smart-Camera-AAL-System\RetrainedModels\\video\\datasets\\ToyotaSmartHome\\')
train_ratio = 0.7
test_ratio = 0.2

split_dataset(root_folder, train_ratio, test_ratio, 'ToyotaSmartHome')
