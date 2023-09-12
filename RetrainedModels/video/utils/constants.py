from enum import Enum


class VideoInference(Enum):
    NUM_EPOCHS = 35
    NUM_CLASSES = 6
    BATCH_SIZE = 10
    NUM_FRAMES = 15
    TRAIN_SUBSET_SIZE = 170
    VAL_SUBSET_SIZE = 40
    TEST_SUBSET_SIZE = 20
    DATASET_DIRECTORY = 'datasets/ToyotaSmartHome/'


class AudioInference(Enum):
    NUM_EPOCHS = 1
    NUM_CLASSES = 3
    BATCH_SIZE = 10
    NUM_FRAMES = 8
    TRAIN_SUBSET_SIZE = 250
    VAL_SUBSET_SIZE = 50
    TEST_SUBSET_SIZE = 50
    DATASET_DIRECTORY = 'datasets/ToyotaSmartHome/'
