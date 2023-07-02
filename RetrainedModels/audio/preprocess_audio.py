import argparse
import os
import csv
from pydub import AudioSegment
import random
from utils.silence_removal import trim_silence, remove_middle_silence
from utils.process_fsd50k import ProcessFSD50k
from utils.process_custom_sounds import ProcessCustomSounds

TRAIN_DS_PERCENTAGE = 0.8
VAL_DS_PERCENTAGE = 0.0
TEST_DS_PERCENTAGE = 0.2

if TRAIN_DS_PERCENTAGE + VAL_DS_PERCENTAGE + TEST_DS_PERCENTAGE != 1:
    raise Exception('train/Val/Test split sum must be equal to 100%')

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--dataset', dest='datasets_path',
                    default='./datasets/', help='Invalid path to datasets!')
args = parser.parse_args()
DATASETS_PATH = args.datasets_path

datasets = [
    ProcessCustomSounds,
    ProcessFSD50k,
    # 'ESC-50',
]

GENERATED_PATH = DATASETS_PATH + 'GENERATED-SOUNDS/'


def read_classes(file):
    classes_read = {}
    i = 0
    with open(file, newline='') as f:
        reader = csv.reader(f)
        iterator = iter(reader)
        next(iterator)
        for row in iterator:
            classes_read[row[0]] = {'id': i, 'count': 0, 'datasets': {}, 'mappings': []}
            i += 1

    print(classes_read)
    return classes_read


def read_vocabulary_mappings(file, classes):
    with open(file, newline='') as f:
        reader = csv.reader(f)
        iterator = iter(reader)
        next(iterator)
        for row in iterator:
            class_name = row[0]
            dataset_name = row[1]
            category_id = row[2]
            matching_category_name = row[3]
            if class_name in classes:
                classes[class_name]['datasets'][dataset_name] = {'id': category_id,
                                                                 'matching_category': matching_category_name}
    print(classes)
    return classes


def read_vocabulary(file):
    vocabulary_read = {}
    with open(file, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            vocabulary_read[row[1]] = row[0]
    return vocabulary_read


def filter(mappings, dataset_name):
    filters_file = 'filters/exclude_files_filter.csv'

    unwanted_files = []
    with open(filters_file, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if dataset_name == row[1]:
                unwanted_files.append(row[0])

    for category in mappings:
        maps = mappings[category]['mappings']
        new_maps = []
        for mapping in maps:
            if mapping[0].split('/')[-1] not in unwanted_files:
                new_maps.append(mapping)

        mappings[category]['mappings'] = new_maps
        mappings[category]['count'] = len(new_maps)

    return mappings


def balance_wav_files(maps):
    # Classe -> Num. total de ficheiros .wav dessa classe (count) -> Array os ficheiros .wav (maps)
    min_count = 99999999
    for mapping in maps:
        if maps[mapping]['count'] < min_count:
            min_count = maps[mapping]['count']

    print("\nClasses to Balance (MIN):", min_count)

    train_ds = int(min_count * TRAIN_DS_PERCENTAGE)
    val_ds = int(min_count * VAL_DS_PERCENTAGE)
    test_ds = int(min_count * TEST_DS_PERCENTAGE)

    dif = min_count - (train_ds + val_ds + test_ds)
    train_ds += dif

    print("train DS size: " + str(train_ds))
    print("Val DS size: " + str(val_ds))
    print("Test DS size: " + str(test_ds))

    # Obter os MIN ficheiros .wav aleatórios de cada classe
    for category in maps:

        train_ds_counter = train_ds
        val_ds_counter = val_ds
        test_ds_counter = test_ds
        new_maps = []

        for line in random.sample(maps[category]['mappings'], min_count):
            if train_ds_counter > 0:
                line[1] = 1
                train_ds_counter -= 1
            elif val_ds_counter > 0:
                line[1] = 2
                val_ds_counter -= 1
            elif test_ds_counter > 0:
                line[1] = 3
                test_ds_counter -= 1
            new_maps.append(line)
        maps[category]['mappings'] = new_maps

    print("\nReady to Write:\n", {'Balanced Classes:': maps})
    return maps


def save_mappings_to_csv(maps):
    i = 0
    with open(GENERATED_PATH + 'mappings.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["filename", "fold", "target", "category", "old_filename"])
        for category in maps:
            for mapping in maps[category]['mappings']:
                mapping.append(mapping[0])
                mapping[3] = category
                mapping[0] = str(i) + '.wav'
                writer.writerow(mapping)
                i += 1


def delete_all_files_from_folder(folder):
    for root, dirs, files in os.walk(folder):
        for file in files:
            os.remove(os.path.join(root, file))


def copy_matching_files(maps):
    audio_preprocessing_operations = [
        trim_silence,
        remove_middle_silence,
    ]

    i = 0
    for category in maps:
        for mapping in maps[category]['mappings']:
            audio = AudioSegment.from_wav(mapping[0])

            # Run preprocessing operations on the audio, only if its not silence
            if category != 'silence':
                for operation in audio_preprocessing_operations:
                    audio = operation(audio)

            audio.export(GENERATED_PATH + "audio/" + str(i) + '.wav', format="wav")
            i += 1


if __name__ == '__main__':
    mappings = read_classes('classes_to_retrain.csv')
    mappings = read_vocabulary_mappings('datasets_vocabulary_mappings.csv', mappings)
    for dataset in datasets:
        mappings = dataset.extract_mappings(DATASETS_PATH, mappings)
    for dataset in datasets:
        mappings = filter(mappings, dataset.getname())

    mappings = balance_wav_files(mappings)
    delete_all_files_from_folder(GENERATED_PATH + "audio")
    copy_matching_files(mappings)
    save_mappings_to_csv(mappings)
