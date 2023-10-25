import socket
import time
import uuid
import random
import datetime

import psutil
from pydub import AudioSegment

from EdgeDevice.InferenceService.audio import AudioInference
import rsa
from collections import deque
import cv2
import numpy as np
from moviepy.editor import *
from pytube import YouTube
import base64
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa as rsaCripto
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import NameOID
import json
import logging
from hashlib import sha256
import netifaces as ni
import platform

# Specify the height and width to which each video frame will be resized in our dataset
IMAGE_HEIGHT, IMAGE_WIDTH = 64, 64
BUFFER_SIZE = 1024
PUBLIC_EXPONENT = 65537
# Specify the list containing the names of the classes used for training.
CLASSES_LIST = ["PushUps", "Punch", "PlayingGuitar", "HorseRace"]

models = {
    'audio': [
        {'name': 'yamnet', 'duration': 0.96, 'frequency': 16000, 'model': AudioInference, 'threshold': 0.2},
        {'name': 'yamnet_retrained', 'duration': 0.96, 'frequency': 16000, 'model': AudioInference, 'threshold': 0.6}
    ],
    'video': [
        # {'name': 'charades', 'model': VideoInference}
    ]
}


def meta(from_id: str, from_ip: str, from_port: int, to_ip="", to_port=0, to_id="", version="0.0.1"):
    """
    Create metadata for a message.

    The `meta` function constructs metadata for a message, including client version and sender/receiver addresses.

    :param from_id: The ID of the message sender.
    :type from_id: str
    :param from_ip: The IP address of the message sender.
    :type from_ip: str
    :param from_port: The port number of the message sender.
    :type from_port: int
    :param to_ip: The IP address of the message receiver.
    :type to_ip: str
    :param to_port: The port number of the message receiver.
    :type to_port: int
    :param to_id: The ID of the message receiver.
    :type to_id: str
    :param version: The version of the client.
    :type version: str

    :return: A dictionary containing message metadata.
    :rtype: dict
    """
    return {
        "CLIENT": version,
        "FROM_ADDRESS": {"ID": from_id, "IP": from_ip, "PORT": from_port},
        "TO_ADDRESS": {"ID": to_id, "IP": to_ip, "PORT": to_port},
    }


class MessageHandlerUtils(object):

    @staticmethod
    def create_general_message(internal_id: str, internal_ip: str, internal_port: int, external_id: str, external_ip: int, external_port: str,
                               node_coordinator: str, message_type: str):
        """
        Create a general message with metadata and payload.

        The `create_general_message` method constructs a general message with metadata and payload components.

        :param internal_id: The internal ID of the message sender.
        :type internal_id: str
        :param internal_ip: The internal IP address of the message sender.
        :type internal_ip: str
        :param internal_port: The internal port number of the message sender.
        :type internal_port: int
        :param external_id: The external ID of the message sender.
        :type external_id: str
        :param external_ip: The external IP address of the message sender.
        :type external_ip: str
        :param external_port: The external port number of the message sender.
        :type external_port: int
        :param node_coordinator: The id of node coordinator.
        :type node_coordinator: str
        :param message_type: The type of the message.
        :type message_type: str

        :return: A dictionary representing the general message.
        :rtype: dict
        """
        return {
            "META": meta(internal_id, internal_ip, internal_port, external_id, external_ip, external_port),
            "TYPE": message_type,
            "PAYLOAD": {
                "LAST_TIME_ALIVE": time.time(),
                "COORDINATOR": node_coordinator,
            },
        }

    @staticmethod
    def create_keep_alive_message(internal_id: str, internal_ip: str, internal_port: int, external_id: str,
                               node_coordinator: str, message_type: str):
        """
        Create a general message with metadata and payload.

        The `create_general_message` method constructs a general message with metadata and payload components.

        :param internal_id: The internal ID of the message sender.
        :type internal_id: str
        :param internal_ip: The internal IP address of the message sender.
        :type internal_ip: str
        :param internal_port: The internal port number of the message sender.
        :type internal_port: int
        :param external_id: The external ID of the message sender.
        :type external_id: str
        :param node_coordinator: The id of node coordinator.
        :type node_coordinator: str
        :param message_type: The type of the message.
        :type message_type: str

        :return: A dictionary representing the general message.
        :rtype: dict
        """
        return {
            "META": meta(internal_id, internal_ip, internal_port, external_id),
            "TYPE": message_type,
            "PAYLOAD": {
                "LAST_TIME_ALIVE": time.time(),
                "COORDINATOR": node_coordinator,
            },
        }

    @staticmethod
    def create_transaction_message(message_type, from_id):
        """
        Create a transaction message.

        The `create_transaction_message` method constructs a transaction message.

        :param message_type: The type of the message.
        :type message_type: str
        :param from_id: The ID of the message sender.
        :type from_id: str

        :return: A dictionary representing the transaction message.
        :rtype: dict
        """
        return {
            "TYPE": message_type,
            "META": {
                "FROM_ADDRESS": {
                    "ID": from_id
                }
            },
            "PAYLOAD": {
            },
        }

    @staticmethod
    def create_event_message(event_action, event_type):
        """
        Create an event message.

        The `create_event_message` method constructs an event message.

        :param event_action: The action associated with the event.
        :type event_action: str
        :param event_type: The type of the event.
        :type event_type: str

        :return: A dictionary representing the event message.
        :rtype: dict
        """
        return {
            "EVENT_ACTION": event_action,
            "EVENT_TYPE": event_type,
        }

    @staticmethod
    def create_homeassistant_message(node_id,event, local):
        """
        Create a Home Assistant message.

        The `create_homeassistant_message` method constructs a Home Assistant message.
        :param node_id: The node id associated with the message.
        :param event: The event associated with the message.
        :type event: str
        :param local: The local status of the message.
        :type local: str
        :return: A dictionary representing the Home Assistant message.
        :rtype: dict
        """
        return {
            "NODE_ID": node_id,
            "TIME": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())),
            "EVENT": event,
            "LOCAL": local,
        }


class Utils(object):
    def compute_hash(self, block):
        """
        Compute the SHA-256 hash of a given block.

        The `compute_hash` method takes a block in dictionary format, converts it to a JSON string, and computes the
        SHA-256 hash of the JSON data.

        :param block: The block to compute the hash for.
        :type block: dict

        :return: The SHA-256 hash of the block.
        :rtype: str
        """
        json_block = self.dict_to_json(block)
        return sha256(json_block.encode()).hexdigest()

    @staticmethod
    def json_to_dict(data):
        """
        Convert JSON data to a Python dictionary.

        The `json_to_dict` method attempts to parse JSON data into a dictionary. If successful, it returns the
        resulting dictionary; otherwise, it logs an error and returns `False`.

        :param data: JSON data to convert.
        :type data: str

        :return: The parsed dictionary or False if the conversion fails.
        :rtype: dict or bool
        """
        try:
            dict_data = json.loads(data)
        except Exception as error:
            logging.error(f'Block: error converting json to dict {error.args}')
            return False
        return dict_data

    @staticmethod
    def dict_to_json(data):
        """
        Convert a Python dictionary to a JSON string.

        The `dict_to_json` method attempts to convert a dictionary to a JSON string. If successful, it returns the
        JSON string; otherwise, it logs an error and returns `False`.

        :param data: The dictionary to convert to JSON.
        :type data: dict

        :return: The JSON representation of the dictionary or False if the conversion fails.
        :rtype: str or bool
        """
        try:
            json_data = json.dumps(data, sort_keys=True)
        except Exception as error:
            logging.error(f'Block: error converting dict to json! {error.args}')
            return False
        return json_data

    @staticmethod
    def validate_dict_keys(data, base_dict):
        """
        Validate that dictionary keys match those of a base dictionary.

        The `validate_dict_keys` method checks if the keys in a given dictionary match the keys of a base dictionary.
        It returns True if the keys match, False if they don't, or False if the input is not a dictionary.

        :param data: The dictionary to validate.
        :type data: dict
        :param base_dict: The base dictionary with expected keys.
        :type base_dict: dict

        :return: True if dictionary keys match those of the base dictionary, False otherwise.
        :rtype: bool
        """
        if not isinstance(data, dict):
            return False
        data_keys = [k for k in data.keys()]
        base_keys = [k for k in base_dict.keys()]
        if sorted(data_keys) != sorted(base_keys):
            logging.error('Server Transaction: Transaction #{} keys are not valid!'.format(data['HEIGHT']))
            return False
        return True

    @staticmethod
    def validate_dict_values(data, base_dict):
        """
        Validate that dictionary values match the expected types in a base dictionary.

        The `validate_dict_values` method checks if the values in a given dictionary match the expected types in a base dictionary.
        It returns True if the values match the expected types, False if they don't, or False if the input is not a dictionary.

        :param data: The dictionary to validate.
        :type data: dict
        :param base_dict: The base dictionary with expected value types.
        :type base_dict: dict

        :return: True if dictionary values match the expected types in the base dictionary, False otherwise.
        :rtype: bool
        """
        if not isinstance(data, dict):
            return False
        keys = [k for k in data.keys()]

        for i in range(len(keys)):
            if type(data[keys[i]]) != base_dict[keys[i]]:
                logging.error('Server Transaction: Transaction #{} values are not valid!'.format(data['HEIGHT']))
                return False
        return True


class NetworkUtils(object):

    @staticmethod
    def display_list_json(list_json):
        """
        Display a list of JSON data in a formatted and readable manner.

        The `display_list_json` method takes a list of JSON data and prints each JSON object with an indentation of 2
        spaces for improved readability. Each JSON object is logged as an informational message.

        :param list_json: A list of JSON objects to display.
        :type list_json: list[dict]
        """
        for json_data in list_json:
            formatted_json = json.dumps(json_data, indent=2)
            logging.info(f"{formatted_json}\n")

    @staticmethod
    def generate_unique_id() -> str:
        """
        Generate a unique identifier by generating a UUID and selecting 10 random digits.

        :return: An string representing the unique identifier.
        """
        # Generate a UUID and convert it to a string
        uuid_str = str(uuid.uuid4())

        # Remove the hyphens and select 10 random digits
        digits = ''.join(random.choice(uuid_str.replace('-', '')) for _ in range(10))

        return digits

    @staticmethod
    def validate(node_connections, ip, port):
        """
        The ``validate`` method checks if a given IP address and port number are already in use by any of the
        existing connections in the node. If the IP address and port number are unique, the method returns True.
        Otherwise, it returns False.

        :param node_connections: The connections that node has
        :type node_connections: <List>
        :param ip: The IP address to validate.
        :type ip: <str>
        :param port: The port number to validate.
        :type port: <int>
        :return: True if the IP address and port number are unique, False otherwise.
        """
        flag = True
        for connection in node_connections:
            if ip != connection.getpeername()[0] and port != connection.getpeername()[1]:
                flag = True
            else:
                flag = False
        return flag

    @staticmethod
    def get_last_event_blockchain(search_type, block_chain_data):

        # Initialize variables to store the last event and timestamp
        last_event = None
        last_event_timestamp = 0

        # Iterate through the data and find the last event with the specified type
        for item in block_chain_data:
            event_data = item.get('DATA', {})
            event_type = event_data.get('EVENT_TYPE', '')
            event_description = event_data.get('EVENT_DESCRIPTION', '')
            event_timestamp = event_data.get('TIMESTAMP', 0)

            if event_type == search_type and event_description == "AUDIO INFERENCE" and event_timestamp > last_event_timestamp:
                last_event_timestamp = event_timestamp
                last_event = item

        # Print the last event with the specified type
        if last_event:
            return json.dumps(last_event, indent=4)
        else:
            logging.warning(f'No event of type {search_type} found')

    @staticmethod
    def get_public_key_by_ip(node_neighbours, ip_address):
        """
        Get the public key associated with a specific IP address.

        The `get_public_key_by_ip` method searches for a matching IP address in the provided `node_neighbours`
        dictionary and returns the associated public key if found.

        :param node_neighbours: A dictionary containing information about node neighbors.
        :type node_neighbours: dict
        :param ip_address: The IP address for which to retrieve the public key.
        :type ip_address: str

        :return: The public key associated with the specified IP address, or None if not found.
        :rtype: str or None
        """
        for neighbour_id, neighbour_info in node_neighbours.items():
            if neighbour_info['IP'] == ip_address:
                return neighbour_info['PUBLIC_KEY']
        return None

    @staticmethod
    def generate_tls_keys():
        """
        The `generate_tls_keys` method generates a new RSA private key and a self-signed TLS certificate.

        Generates a new RSA private key using the specified public exponent and key size. Then, creates a self-signed TLS
        certificate without a common name, using the provided subject and issuer information. The certificate is valid for
        one year from the current date. The private key and certificate are saved to file's in the 'Keys' folder within the
        current working directory.

        :return: None
        """
        # Generate a new RSA private key
        private_key = rsaCripto.generate_private_key(
            public_exponent=PUBLIC_EXPONENT,
            key_size=BUFFER_SIZE * 2
        )

        # Create a self-signed certificate without a common name
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"PT"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Porto"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, u"Porto"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"UFP"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, u"Engineering"),
        ])

        cert = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).serial_number(
            x509.random_serial_number()).public_key(private_key.public_key()).not_valid_before(
            datetime.utcnow()).not_valid_after(datetime.utcnow() + timedelta(days=365)).sign(private_key,
                                                                                             hashes.SHA256())

        current_directory = os.getcwd()
        keys_folder = os.path.join(current_directory, 'Keys')

        # Write the private key and certificate to files
        with open(os.path.join(keys_folder, 'key.pem'), "wb") as key_file:
            key_file.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))

        with open(os.path.join(keys_folder, 'cert.pem'), "wb") as cert_file:
            cert_file.write(cert.public_bytes(serialization.Encoding.PEM))

    @staticmethod
    def get_interface_ip():
        """
        Get the IP address associated with the specified network interface.

        The `get_interface_ip` method retrieves the IP address associated with the network interface named 'Wi-fi'
        on Windows or 'eth0' on Linux. It may return None if the platform is not supported or if the interface
        is not found.

        :return: The IP address associated with the specified network interface, or None if not found.
        :rtype: str or None
        """
        if platform.system() == 'Windows':
            interface = 'Wi-fi'
            try:
                interfaces = psutil.net_if_addrs()
                if interface in interfaces:
                    addresses = interfaces[interface]
                    for address in addresses:
                        if address.family == socket.AF_INET:
                            return address.address
                else:
                    return None
            except Exception as e:
                print("Error:", e)
                return None
        elif platform.system() == 'Linux':
            # Replace 'eth0' with the actual interface name on Linux if needed
            interface = 'eth0'
        else:
            return None

        # Retrieve the IP address from the network interface on Linux
        return ni.ifaddresses(interface)[ni.AF_INET][0]['addr']

    @staticmethod
    def generate_keys():
        """
        The `generate_keys` method generates a pair of RSA public and private keys and saves them as PEM files in the
        'Keys' folder.

        The function first obtains the current directory. It creates a folder named 'Keys' within the current directory
        if it doesn't already exist. Then, it generates a new pair of RSA public and private keys using the RSA algorithm
        with a specified key size (BUFFER_SIZE). The public and private keys are obtained as separate objects.

        Next, the function saves the public key to a file named 'public.pem' in the 'Keys' folder. The public key is
        serialized in the PEM format and written to the file.

        Similarly, the function saves the private key to a file named 'private.pem' in the 'Keys' folder. The private key
        is also serialized in the PEM format and written to the file.

        :return: None
        """
        current_directory = os.getcwd()
        keys_folder = os.path.join(current_directory, 'Keys')
        public_key, private_key = rsa.newkeys(BUFFER_SIZE)

        with open(os.path.join(keys_folder, 'public.pem'), "wb") as f:
            f.write(public_key.save_pkcs1("PEM"))

        with open(os.path.join(keys_folder, 'private.pem'), "wb") as f:
            f.write(private_key.save_pkcs1("PEM"))

    @staticmethod
    def get_keys():
        """
        The `get_tls_keys` method retrieves the RSA private and public keys from the specified keys' folder.

        Retrieves the RSA private key and public key from the specified keys' folder. The current working directory is
        obtained, and the keys' folder is determined by joining the current directory with the 'Keys' folder name. The
        private key is loaded from the 'private.pem' file within the keys' folder using the RSA algorithm. Similarly, the
        public key is loaded from the 'public.pem' file within the keys' folder. The loaded private key and public key are
        returned as a tuple.

        :return: The RSA private key and the RSA public key.
        :rtype: tuple[rsa.PrivateKey, rsa.PublicKey]
        """
        current_directory = os.getcwd()
        keys_folder = os.path.join(current_directory, 'Keys')

        with open(os.path.join(keys_folder, 'public.pem'), "rb") as f:
            public_key = rsa.PublicKey.load_pkcs1(f.read())

        with open(os.path.join(keys_folder, 'private.pem'), "rb") as f:
            private_key = rsa.PrivateKey.load_pkcs1(f.read())

        return private_key, public_key

    @staticmethod
    def get_tls_keys():
        """
        The `get_tls_keys` method retrieves the paths to the TLS certificate and key files.

        Retrieves the paths to the TLS certificate file and key file from the specified keys' folder. The current working
        directory is obtained, and the keys' folder is determined by joining the current directory with the 'Keys' folder
        name. The paths to the certificate file (cert.pem) and key file (key.pem) within the keys' folder are returned.

        :return: The path to the TLS certificate file and the path to the TLS key file.
        :rtype: tuple[str, str]
        """
        current_directory = os.getcwd()
        keys_folder = os.path.join(current_directory, 'Keys')
        cert_pem = os.path.join(keys_folder, 'cert.pem')
        key_pem = os.path.join(keys_folder, 'key.pem')

        return cert_pem, key_pem

    @staticmethod
    def load_key_from_json(public_key_json):
        """
        The `load_public_key_from_json` method loads a public key object from a JSON-compatible representation.

        Deserializes a public key object from a JSON-compatible representation. The provided JSON string is first decoded
        from Base64 to obtain the corresponding bytes. The bytes are then loaded as a PKCS#1 formatted public key using
        the RSA algorithm. The resulting public key object is returned.

        :param public_key_json: The JSON-compatible representation of the public key.
        :type public_key_json: str
        :return: The loaded public key object.
        :rtype: RSA.RSAPublicKey
        """
        public_key_bytes = base64.b64decode(public_key_json.encode('utf-8'))
        public_key = rsa.PublicKey.load_pkcs1(public_key_bytes, format='PEM')
        return public_key

    @staticmethod
    def key_to_json(public_key):
        """
        The `public_key_to_json` method converts a public key object to a JSON-compatible representation.

        Serializes the provided public key object to a JSON-compatible representation. The public key is first saved in the
        PKCS#1 format as bytes, then encoded using Base64 to obtain a string representation. The resulting Base64 string
        representation of the public key is returned.

        :param public_key: The public key object to be converted.
        :type public_key: RSA.RSAPublicKey
        :return: The JSON-compatible representation of the public key.
        :rtype: str
        """
        public_key_bytes = public_key.save_pkcs1(format='PEM')
        public_key_base64 = base64.b64encode(public_key_bytes).decode('utf-8')
        return public_key_base64


class InferenceUtils(object):

    def handle_detection(self):
        """
        The `handle_detection` method handles the detection of actions in a video by performing action recognition using
        a pre-trained model.

        The function first creates the output directory for storing the test videos if it does not already exist. It then
        downloads a YouTube video specified by its URL and retrieves the title of the downloaded video. The path to the
        downloaded video file is obtained.

        Next, the pre-trained action recognition model is loaded from the specified file path. The model is assumed to be
        trained on a Long-term Recurrent Convolutional Network (LRCN).

        Finally, the loaded model is used to perform action recognition on the test video. The number of predicted classes
        is specified as 20. The class prediction result is printed.

        :return: None
        """
        # Make the output directory if it does not exist
        test_videos_directory = 'test_videos'
        os.makedirs(test_videos_directory, exist_ok=True)

        # Download a YouTube video
        video_title = self.download_youtube_videos('https://youtube.com/watch?v=iNfqx2UCu-g', test_videos_directory)
        print(f"Downloaded video title: {video_title}")

        # Get the YouTube video's path we just downloaded
        input_video_file_path = f'{test_videos_directory}/{video_title}.mp4'

        # Load Model
        # model = tf.keras.models.load_model(
        #    '../EdgeDevice/models/LRCN_model__Date_time_2023_05_23__00_06_42__Loss_0.23791147768497467__Accuracy_0.971222996711731.h5')

        # Perform action recognition on the test video
        # class_prediction = predict_on_video(model, input_video_file_path, 20)
        # print("[CLASS_PREDICTION] : ", class_prediction)

    def data_processing_worker(self, in_q, out_q):
        """
        Process data items from the input queue and send processed items to the output queue.

        The `data_processing_worker` method continuously processes data items from the `in_q` queue. For each data item,
        it iterates through the specified models and creates a new item with updated information, which is then placed
        into the `out_q` queue.

        :param in_q: The input queue for receiving data items.
        :type in_q: queue.Queue
        :param out_q: The output queue for sending processed data items.
        :type out_q: queue.Queue
        """
        while True:
            item = in_q.get()
            for model in models[item['type']]:
                new_item = {'type': item['type'], 'name': model['name'], 'data': item['data'][:]}
                out_q.put(new_item)

    def inference_worker(self, in_q, out_q):
        """
        Perform inference on data items from the input queue and send results to the output queue.

        The `inference_worker` method initializes local models for audio and video based on the specified configurations.
        It continuously retrieves data items from the `in_q` queue, performs inference using the corresponding model,
        and puts the prediction result into the `out_q` queue.

        :param in_q: The input queue for receiving data items.
        :type in_q: queue.Queue
        :param out_q: The output queue for sending inference results.
        :type out_q: queue.Queue
        """
        local_models = {}
        for audio_model in models['audio']:
            model = audio_model['model'](audio_model)
            local_models[audio_model['name']] = model

        for video_model in models['video']:
            model = video_model['model']()
            local_models[video_model['name']] = model

        while True:
            item = in_q.get()
            prediction = local_models[item['name']].inference(item['data'])
            if prediction != 'Unknown':
                out_q.put({'prediction': prediction, 'type': item['type'], 'timestamp': str(datetime.datetime.now())})

    def network_worker(self, in_q):
        """
        Process network-related tasks for items from the input queue.

        The `network_worker` method continuously processes network-related tasks from the `in_q` queue. It includes a
        delay of one second for simulating network activity and prints the received item.

        :param in_q: The input queue for receiving network-related tasks.
        :type in_q: queue.Queue
        """
        while True:
            item = in_q.get()
            time.sleep(1)
            print(item)

    def download_youtube_videos(self, youtube_video_url, output_directory):
        """
           This function downloads the YouTube video whose URL is passed to it as an argument.
           :param youtube_video_url: URL of the video that is required to be downloaded
           :param output_directory: The directory path to which the video needs to be stored after downloading
           :return title: The title of the downloaded YouTube video.
        """

        yt = YouTube(youtube_video_url)
        yt.title = yt.title.replace(' ', '_').replace('/', '').replace(',', '')

        yt.streams.filter(adaptive=True)
        output_file_path = os.path.join(output_directory)
        yt.streams.get_highest_resolution().download(output_path=output_file_path)

        return yt.title

    def predict_on_video(self, model, video_file_path, SEQUENCE_LENGTH):
        """
        This function will perform action recognition on a video using the LRCN model
        :param model: The model to make prediction
        :param video_file_path: The path of the video stored in the disk on which the action recognition is to be performed
        :param SEQUENCE_LENGTH: The fixed number of frames of a video that can be passed to the model as one sequence.
        :return: None
        """

        # Initialize the VideoCapture object to read from the video file.
        video_reader = cv2.VideoCapture(video_file_path)

        # Declare a queue to store video frames
        frames_queue = deque(maxlen=SEQUENCE_LENGTH)

        # Initialize a variable to store the predicted action being performed in the video
        predicted_class_name = ''

        # Iterate until the video is accessed successfully
        while video_reader.isOpened():

            # Read the frame
            ok, frame = video_reader.read()

            # Check if frame is not read properly then break the loop.
            if not ok:
                break

            # Resize the frame to fixed Dimensions
            resized_frame = cv2.resize(frame, (IMAGE_HEIGHT, IMAGE_WIDTH))

            # Normalize the resized frame by diving it with 255 so that each pixel value then lies between 0 and 1
            normalized_frame = resized_frame / 255

            # Appending the pre-processed frame into the frames list
            frames_queue.append(normalized_frame)

            # Check if the number of frames in the queue are equal to the fixed sequence length.
            if len(frames_queue) == SEQUENCE_LENGTH:
                # Pass the normalized frames to the model and get the predicted probabilities
                predicted_labels_probabilities = model.predict(np.expand_dims(frames_queue, axis=0))[0]

                print("Predicted Accuracy: ", predicted_labels_probabilities)

                # Get the index of class with highest probability
                predicted_label = np.argmax(predicted_labels_probabilities)

                # Get the class name using the retrieved index
                predicted_class_name = CLASSES_LIST[predicted_label]
                break

        return predicted_class_name

    def remove_middle_silence(self, sound):
        """
            Removes silence from the middle of an audio signal.
            :param sound (pydub.AudioSegment): An audio signal to process.
            :returns pydub.AudioSegment: A copy of the input signal with middle silence removed.
        """
        silence_threshold = -45.0  # dB
        chunk_size = 100  # ms
        sound_ms = 0  # ms
        trimmed_sound = AudioSegment.empty()

        while sound_ms < len(sound):
            if sound[sound_ms:sound_ms + chunk_size].dBFS >= silence_threshold:
                trimmed_sound += sound[sound_ms:sound_ms + chunk_size]
            sound_ms += chunk_size

        return trimmed_sound.set_sample_width(2)
