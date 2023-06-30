import collections
import csv
import os
import pathlib
import random
import cv2
import imageio
import numpy as np
import remotezip as rz
import tensorflow as tf
import tqdm
from tensorflow_docs.vis import embed


class CharadesDataset:
    def __init__(self, csv_file, txt_action_file, output_directory):
        self.csv_file = csv_file
        self.txt_action_file = txt_action_file
        self.output_directory = output_directory

    def create_dir_actions(self):
        # Create the output directory if it doesn't exist
        os.makedirs(self.output_directory, exist_ok=True)

        # Read the CSV file and extract the values from the second column
        with open(self.csv_file, 'r') as file:
            reader = csv.reader(file)
            next(reader)  # Skip the header row if it exists
            for row in reader:
                action_value = row[0][5:]
                folder_name = action_value.replace(' ', '_')  # Replace spaces with underscores for the folder name
                folder_name = folder_name.replace('/', '_')  # Replace / with underscores for the folder name
                folder_path = os.path.join(self.output_directory, folder_name)
                os.makedirs(folder_path, exist_ok=True)

    def create_actions_files_dir(self, video_directory):
        # Create an empty list to store JSON objects
        json_list = []
        action_list = []

        # Read the CSV file
        with open(self.csv_file, 'r') as file:
            reader = csv.reader(file)

            for line in reader:
                id_value = line[0]
                actions_value = line[9]

                # Extract the desired format from the actions_value
                actions_list = actions_value.split(';')  # Split the actions_value by semicolon
                actions_list = [action.split(' ')[0] for action in actions_list]  # Extract the action part

                data = {
                    "id": id_value,
                    "action": ";".join(actions_list)  # Join the actions_list with semicolon as separator
                }
                json_list.append(data)  # Append each JSON object to the list

        with open(self.txt_action_file, 'r') as fileaction:
            reader_action = csv.reader(fileaction)
            next(reader_action)  # Skip the header row if it exists
            for row in reader_action:
                action = {"action_id": row[0][:4], "action_description": row[0][5:]}
                action_list.append(action)

        matching_actions = self.compare_json_lists(action_list, json_list)
        self.map_files_to_action_directory(video_directory, matching_actions)

    @staticmethod
    def compare_json_lists(action_list, json_list):
        matching_actions = []
        for json_obj in json_list:
            json_id = json_obj["id"]
            json_actions = json_obj["action"].split(";")  # Split the concatenated actions

            for json_action in json_actions:
                # Check if json_action ID exists in the action list
                matching_action = next((action for action in action_list if action["action_id"] == json_action), None)

                # If a matching action is found, compare the IDs
                if matching_action:
                    action_id = matching_action["action_id"]
                    action_description = matching_action["action_description"].replace(' ', '_')
                    action_description = action_description.replace('/', '_')
                    match_json = {"action_id": action_id, "action_description": action_description,
                                  "video_id": json_id}
                    matching_actions.append(match_json)

        return matching_actions

    def map_files_to_action_directory(self, video_directory, json_list):
        for json_obj in json_list:
            video_id = json_obj["video_id"]
            action_description = json_obj["action_description"]
            action_directory = os.path.join(self.output_directory, action_description)
            os.makedirs(action_directory, exist_ok=True)
            print(action_description)
            file_path = os.path.join(video_directory, video_id + ".mp4")
            if os.path.exists(file_path):
                destination_path = os.path.join(action_directory, video_id + ".mp4")
                os.rename(file_path, destination_path)
                print(f"Arquivo {video_id} movido para o diretório {destination_path}")


class ToyotaSmartHomeDataset:
    def __init__(self, video_directory, output_directory):
        self.video_directory = video_directory
        self.output_directory = output_directory

    def create_dir_actions(self):
        # Create the output directory if it doesn't exist
        os.makedirs(self.output_directory, exist_ok=True)

        for filename in os.listdir(self.video_directory):
            folder_name = filename.split("_")[0].replace(".", "_")
            folder_path = os.path.join(self.output_directory, folder_name)
            os.makedirs(folder_path, exist_ok=True)

    def map_files_to_action_directory(self):
        for filename in os.listdir(self.video_directory):
            folder_name = filename.split("_")[0].replace(".", "_")
            filename_path = os.path.join(self.video_directory, filename)
            folder_path = os.path.join(self.output_directory, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            if os.path.exists(filename_path):
                destination_path = os.path.join(folder_path, filename)
                os.rename(filename_path, destination_path)
                print(f"Arquivo {filename} movido para o diretório {folder_path}")


class UCF101Dataset:
    def __init__(self, URL, output_directory):
        self.URL = URL
        self.dirs = self.download_ufc_101_subset(URL,
                                                 num_classes=10,
                                                 splits={"train": 40, "val": 10, "test": 10},
                                                 download_dir=output_directory)

    @staticmethod
    def list_files_per_class(zip_url):
        """
          List the files in each class of the dataset given the zip URL.

          Args:
            zip_url: URL from which the files can be unzipped.

          Return:
            files: List of files in each of the classes.
        """
        files = []
        with rz.RemoteZip(zip_url) as zipelement:
            for zip_info in zipelement.infolist():
                files.append(zip_info.filename)
        return files

    @staticmethod
    def get_class(fname):
        """
          Retrieve the name of the class given a filename.

          Args:
            fname: Name of the file in the UCF101 dataset.

          Return:
            Class that the file belongs to.
        """
        return fname.split('_')[-3]

    def get_files_per_class(self, files):
        """
          Retrieve the files that belong to each class.

          Args:
            files: List of files in the dataset.

          Return:
            Dictionary of class names (key) and files (values).
        """
        files_for_class = collections.defaultdict(list)
        for fname in files:
            class_name = self.get_class(fname)
            files_for_class[class_name].append(fname)
        return files_for_class

    def download_from_zip(self, zip_url, to_dir, file_names):
        """
          Download the contents of the zip file from the zip URL.

          Args:
            zip_url: Zip URL containing data.
            to_dir: Directory to download data to.
            file_names: Names of files to download.
        """
        with rz.RemoteZip(zip_url) as zipelement:
            for fn in tqdm.tqdm(file_names):
                class_name = self.get_class(fn)
                zipelement.extract(fn, str(to_dir / class_name))
                unzipped_file = to_dir / class_name / fn

                fn = pathlib.Path(fn).parts[-1]
                output_file = to_dir / class_name / fn
                unzipped_file.rename(output_file, )

    @staticmethod
    def split_class_lists(files_for_class, count):
        """
          Returns the list of files belonging to a subset of data as well as the remainder of
          files that need to be downloaded.

          Args:
            files_for_class: Files belonging to a particular class of data.
            count: Number of files to download.

          Return:
            split_files: Files belonging to the subset of data.
            remainder: Dictionary of the remainder of files that need to be downloaded.
        """
        split_files = []
        remainder = {}
        for cls in files_for_class:
            split_files.extend(files_for_class[cls][:count])
            remainder[cls] = files_for_class[cls][count:]
        return split_files, remainder

    def download_ufc_101_subset(self, zip_url, num_classes, splits, download_dir):
        """
          Download a subset of the UFC101 dataset and split them into various parts, such as
          training, validation, and test.

          Args:
            zip_url: Zip URL containing data.
            num_classes: Number of labels.
            splits: Dictionary specifying the training, validation, test, etc. (key) division of data
                    (value is number of files per split).
            download_dir: Directory to download data to.

          Return:
            dir: Posix path of the resulting directories containing the splits of data.
        """
        files = self.list_files_per_class(zip_url)
        for f in files:
            tokens = f.split('/')
            if len(tokens) <= 2:
                files.remove(f)  # Remove that item from the list if it does not have a filename

        files_for_class = self.get_files_per_class(files)

        classes = list(files_for_class.keys())[:num_classes]

        for cls in classes:
            new_files_for_class = files_for_class[cls]
            random.shuffle(new_files_for_class)
            files_for_class[cls] = new_files_for_class

        # Only use the number of classes you want in the dictionary
        files_for_class = {x: files_for_class[x] for x in list(files_for_class)[:num_classes]}

        dirs = {}
        for split_name, split_count in splits.items():
            print(split_name, ":")
            split_dir = download_dir / split_name
            split_files, files_for_class = self.split_class_lists(files_for_class, split_count)
            self.download_from_zip(zip_url, split_dir, split_files)
            dirs[split_name] = split_dir

        return dirs

    @staticmethod
    def format_frames(frame, output_size):
        """
          Pad and resize an image from a video.

          Args:
            frame: Image that needs to resized and padded.
            output_size: Pixel size of the output frame image.

          Return:
            Formatted frame with padding of specified output size.
        """
        frame = tf.image.convert_image_dtype(frame, tf.float32)
        frame = tf.image.resize_with_pad(frame, *output_size)
        return frame

    def frames_from_video_file(self, video_path, n_frames, output_size=(172, 172), frame_step=15):
        """
          Creates frames from each video file present for each category.

          Args:
            :param video_path: File path to the video.
            :param n_frames: Number of frames to be created per video file.
            :param output_size: Pixel size of the output frame image.
            :param frame_step:

          Return:
            An NumPy array of frames in the shape of (n_frames, height, width, channels).
        """
        # Read each video frame by frame
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
        # ret is a boolean indicating whether read was successful, frame is the image itself
        ret, frame = src.read()
        result.append(self.format_frames(frame, output_size))

        for _ in range(n_frames - 1):
            for _ in range(frame_step):
                ret, frame = src.read()
            if ret:
                frame = self.format_frames(frame, output_size)
                result.append(frame)
            else:
                result.append(np.zeros_like(result[0]))
        src.release()
        result = np.array(result)[..., [2, 1, 0]]

        return result

    @staticmethod
    def to_gif(images):
        converted_images = np.clip(images * 255, 0, 255).astype(np.uint8)
        imageio.mimsave('./animation.gif', converted_images, fps=10)
        return embed.embed_file('./animation.gif')

    class FrameGenerator:
        def __init__(self, path, n_frames, training=False):
            """ Returns a set of frames with their associated label.

              Args:
                path: Video file paths.
                n_frames: Number of frames.
                training: Boolean to determine if training dataset is being created.
            """
            self.path = path
            self.n_frames = n_frames
            self.training = training
            self.class_names = sorted(set(p.name for p in self.path.iterdir() if p.is_dir()))
            self.class_ids_for_name = dict((name, idx) for idx, name in enumerate(self.class_names))

        def get_files_and_class_names(self):
            video_paths = list(self.path.glob('*/*.avi'))
            classes = [p.parent.name for p in video_paths]
            return video_paths, classes

        def __call__(self):
            video_paths, classes = self.get_files_and_class_names()

            pairs = list(zip(video_paths, classes))

            if self.training:
                random.shuffle(pairs)

            for path, name in pairs:
                video_frames = UCF101Dataset.frames_from_video_file(path, self.n_frames)
                label = self.class_ids_for_name[name]  # Encode labels
                yield video_frames, label


def main():
    # Charades dataset
    charades_csv_file = 'models/charades/Charades_v1_train.csv'
    charades_txt_action_file = 'models/charades/Charades_v1_classes.txt'
    charades_output_directory = './datasets/Charades/'
    charades_video_directory = './datasets/Charades/Charades_v1_480/'

    charades_dataset = CharadesDataset(charades_csv_file, charades_txt_action_file, charades_output_directory)
    charades_dataset.create_dir_actions()
    charades_dataset.create_actions_files_dir(charades_video_directory)

    # Toyota Smarthome dataset
    toyota_video_directory = './datasets/ToyotaSmartHome/mp4/'
    toyota_output_directory = './datasets/ToyotaSmartHome/'

    toyota_dataset = ToyotaSmartHomeDataset(toyota_video_directory, toyota_output_directory)
    toyota_dataset.create_dir_actions()
    toyota_dataset.map_files_to_action_directory()

    # UCF101 dataset
    url_ucf101_dataset = "https://storage.googleapis.com/thumos14_files/UCF101_videos.zip"
    ucf101_output_directory = pathlib.Path('datasets/UCF101/')
    ucf101_dataset = UCF101Dataset(url_ucf101_dataset, ucf101_output_directory)
    print(ucf101_dataset.dirs)


if __name__ == '__main__':
    main()
