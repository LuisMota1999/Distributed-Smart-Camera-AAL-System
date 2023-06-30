import csv

DATASET_NAME = 'FSD50k'


class ProcessFSD50k:

    @staticmethod
    def extract_mappings(datasets_path, mappings):
        dataset_path = datasets_path + DATASET_NAME + '/'
        mappings = ProcessFSD50k.extract_custom(dataset_path, 'dev', mappings)
        mappings = ProcessFSD50k.extract_custom(dataset_path, 'eval', mappings)

        return mappings

    @staticmethod
    def getname():
        return DATASET_NAME

    @staticmethod
    def extract_custom(dataset_path, type, mappings):
        mappings_file = dataset_path + type + '.csv'
        audio_folder = dataset_path + 'audio-' + type
        with open(mappings_file, newline='') as f:
            reader = csv.reader(f)
            iterreader = iter(reader)
            next(iterreader)
            for row in iterreader:
                categories = row[1].split(',')
                for category in categories:
                    for class_maps in mappings:
                        for dataset in mappings[class_maps]['datasets']:
                            if category == mappings[class_maps]['datasets'][dataset]['matching_category']:
                                mappings[class_maps]['count'] += 1
                                mappings[class_maps]['mappings'].append(
                                    [audio_folder + "/" + row[0] + ".wav", str(0), mappings[class_maps]['id'],
                                     category])
        return mappings

