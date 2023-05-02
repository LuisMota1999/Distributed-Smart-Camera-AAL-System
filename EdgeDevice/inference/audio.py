import numpy as np
from tflite_runtime.interpreter import Interpreter
from pydub import AudioSegment
import csv


class AudioInference:
    """
        A class for performing audio inference using TensorFlow Lite models.
        :arg fs (int): Sample rate in Hz.
        :arg samples (int): Number of audio samples in each input signal.
        :arg model_name (str): Name of the loaded model.
        :arg threshold (float): Confidence threshold for classification.
        :arg interpreter (tflite_runtime.interpreter.Interpreter): TensorFlow Lite interpreter.
        :arg waveform_input_index (int): Index of waveform input tensor.
        :arg  scores_output_index (int): Index of scores output tensor.
        :arg class_names (list): List of class names for the loaded model.
    """
    def __init__(self, audio_model):
        """
            Initializes an instance of the AudioInference class.
            :param audio_model: A dictionary containing the parameters for the loaded model.
            :type audio_model: dict
        """
        self.fs = audio_model['frequency']  # sample rate (Hz)
        duration = audio_model['duration']  # seconds, ex. multiple of 0.96 for yamnet (length of the sliding window)
        self.samples = int(duration * self.fs)
        self.model_name = audio_model['name']
        self.threshold = audio_model['threshold']  # threshold from 0 to 1, ex. 0.85

        # Load Model
        self.interpreter = Interpreter(f'models/{self.model_name}.tflite')
        inputs = self.interpreter.get_input_details()
        outputs = self.interpreter.get_output_details()
        self.waveform_input_index = inputs[0]['index']
        self.scores_output_index = outputs[0]['index']

        # Read the csv file containing the model classes
        class_map_path = f'models/{self.model_name}_class_map.csv'
        with open(class_map_path) as class_map_csv:
            self.class_names = [display_name for (class_index, mid, display_name) in csv.reader(class_map_csv)]
        self.class_names = self.class_names[1:]  # Skip CSV header

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

    def inference(self, waveform):
        """
        This method inference is responsible for performing audio inference on a given waveform using a pre-trained
        TFLite model. The method first reshapes the waveform array to the appropriate length self.samples and
        converts it to a float32 data type. Then, the method resizes the tensor input of the interpreter to match the
        length of the waveform and sets the tensor to the given waveform. The interpreter is then invoked to perform
        inference and return the scores. If the model is a YAMNet model, then the scores are averaged along the first
        axis, otherwise the softmax function is simulated to compute the class probabilities. The method then
        determines the top class label and its corresponding score, and retrieves the inferred class label from the
        pre-loaded class names. If the top score is below a certain threshold, the inferred class label is set to
        'Unknown'. Finally, the method prints the inferred class label and its corresponding score and returns the
        inferred class label.

        :param waveform: A numpy array representing the audio waveform.
        :return: A string representing the inferred class label.
        """
        waveform.shape = (self.samples,)
        waveform = waveform.astype('float32')

        # audio = AudioSegment.from_wav('tmp.wav')
        # audio = self.remove_middle_silence(audio)
        # audio.export(filename, format="wav")

        self.interpreter.resize_tensor_input(self.waveform_input_index, [len(waveform)], strict=True)
        self.interpreter.allocate_tensors()
        self.interpreter.set_tensor(self.waveform_input_index, waveform)
        self.interpreter.invoke()
        scores = self.interpreter.get_tensor(self.scores_output_index)

        # compute softmax activations
        if self.model_name == 'yamnet':
            class_probabilities = np.mean(scores, axis=0)  # yamnet non-retrained model uses different activations
        else:
            class_probabilities = np.exp(scores) / np.sum(np.exp(scores), axis=-1)  # simulate tf softmax function

        top_class = np.argmax(class_probabilities)
        top_score = class_probabilities[top_class]
        inferred_class = self.class_names[top_class]

        if top_score < self.threshold:
            inferred_class = 'Unknown'

        print(f'[AUDIO - \'{self.model_name}\'] {inferred_class} ({top_score})')

        return inferred_class
