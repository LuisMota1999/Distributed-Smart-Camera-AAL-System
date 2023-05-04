import numpy as np
import sounddevice as sd

fs = 16000  # sample rate (Hz)
duration = 0.96  # seconds, multiple of 0.96 (length of the sliding window)
samples = int(duration * fs)


class MicrophoneAudioStream:
    def __init__(self, src, in_q):
        """
            Initializes a MicrophoneAudioStream object.

            :param src: input source (e.g. microphone device index)
            :type src: int or str
            :param in_q: input queue to put the recorded audio data into
            :type in_q: multiprocessing.Queue object
        """
        # initialize the audio input stream
        self.stream = sd.InputStream(samplerate=fs, channels=1, callback=self.update)
        self.in_q = in_q
        self.recording = np.zeros((0, 1))

    def start(self):
        """
        Starts the audio input stream.

        :return: self object
        """
        self.stream.start()
        return self

    def update(self, indata, frames, time, status):
        """
            Updates the recording array with the new audio data and adds it to the input queue when the recording array
            reaches the specified length.

            :param indata: audio data from the microphone
            :type indata: numpy.ndarray
            :param frames: number of frames
            :type frames: int
            :param time: timestamp
            :type time: sd.TimeStruct
            :param status: status flags
            :type status: sd.CallbackFlags
            :returns: None
        """
        self.recording = np.concatenate((self.recording, indata), axis=0)

        if self.recording.size >= samples:
            item = {"type": "audio", 'data': self.recording[:samples]}
            self.in_q.put(item)
            self.recording = self.recording[samples:]

    def stop(self):
        """
            Stops the audio input stream.
            :returns: None
        """
        self.stream.stop()
