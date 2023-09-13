from enum import Enum


class VideoInference(Enum):
    NUM_EPOCHS = 5
    NUM_CLASSES = 3
    BATCH_SIZE = 10
    NUM_FRAMES = 8
    TRAIN_SUBSET_SIZE = 100
    VAL_SUBSET_SIZE = 15
    TEST_SUBSET_SIZE = 15
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
