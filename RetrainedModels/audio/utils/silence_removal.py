from pydub import AudioSegment


# Iterate over chunks until you find the first one with sound, where sound is a pydub.AudioSegment
def detect_leading_silence(sound):
    silence_threshold = -50.0  # dB
    chunk_size = 10  # ms
    trim_ms = 0  # ms

    while sound[trim_ms:trim_ms+chunk_size].dBFS < silence_threshold and trim_ms < len(sound):
        trim_ms += chunk_size

    return trim_ms


# Iterate over chunks of the sound, removing ones with silence, where sound is a pydub.AudioSegment
def remove_middle_silence(sound):
    silence_threshold = -50.0  # dB
    chunk_size = 100  # ms
    sound_ms = 0  # ms
    trimmed_sound = AudioSegment.empty()

    while sound_ms < len(sound):
        if sound[sound_ms:sound_ms+chunk_size].dBFS >= silence_threshold:
            trimmed_sound += sound[sound_ms:sound_ms+chunk_size]
        sound_ms += chunk_size

    return trimmed_sound.set_sample_width(2)


def trim_silence(sound):
    start_trim = detect_leading_silence(sound)
    end_trim = detect_leading_silence(sound.reverse())

    duration = len(sound)
    trimmed_sound = sound[start_trim:duration - end_trim]
    return trimmed_sound
