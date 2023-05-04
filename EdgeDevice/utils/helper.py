import uuid
import random
import datetime
from EdgeDevice.InferenceService.audio import AudioInference

models = {
    'audio': [
        {'name': 'yamnet', 'duration': 0.96, 'frequency': 16000, 'model': AudioInference, 'threshold': 0.2},
        {'name': 'yamnet_retrained', 'duration': 0.96, 'frequency': 16000, 'model': AudioInference, 'threshold': 0.6}
    ],
    'video': [
        # {'name': 'charades', 'model': VideoInference}
    ]
}


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


def data_processing_worker(in_q, out_q):
    while True:
        item = in_q.get()
        for model in models[item['type']]:
            new_item = {'type': item['type'], 'name': model['name'], 'data': item['data'][:]}
            out_q.put(new_item)


def inference_worker(in_q, out_q):
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


def network_worker(in_q):
    while True:
        item = in_q.get()
