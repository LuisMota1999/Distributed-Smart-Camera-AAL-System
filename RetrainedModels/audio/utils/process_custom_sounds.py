import csv

DATASET_NAME = 'CUSTOM-SOUNDS'


class ProcessCustomSounds:

    @staticmethod
    def extract_mappings(datasets_path, mappings):
        dataset_path = datasets_path + DATASET_NAME + '/'
        mappings_file = dataset_path + 'mappings.csv'
        audio_folder = dataset_path + 'audio'
        vocabulary = ProcessCustomSounds.read_vocabulary(dataset_path)

        with open(mappings_file, newline='') as f:
            reader = csv.reader(f)
            iterreader = iter(reader)
            next(iterreader)
            for row in iterreader:
                category_id = row[1]
                category = vocabulary[category_id]

                for class_maps in mappings:
                    for dataset in mappings[class_maps]['datasets']:
                        if category == mappings[class_maps]['datasets'][dataset]['matching_category']:
                            mappings[class_maps]['count'] += 1
                            mappings[class_maps]['mappings'].append(
                                [audio_folder + "/" + row[0] + ".wav", str(0), mappings[class_maps]['id'], category])
        return mappings

    @staticmethod
    def getname():
        return DATASET_NAME

    @staticmethod
    def read_vocabulary(dataset_path):
        vocabulary = {}
        vocabulary_file = dataset_path + 'vocabulary.csv'
        with open(vocabulary_file, newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                vocabulary[row[0]] = row[1]

        return vocabulary
