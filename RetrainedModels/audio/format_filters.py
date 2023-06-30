import csv

classes = [
    {'filename': 'boiling.csv', 'category': 'Boiling'},
    {'filename': 'doorbell.csv', 'category': 'Doorbell'},
    {'filename': 'dishes_and_pots_and_pans.csv', 'category': 'Dishes_and_pots_and_pans'},
    {'filename': 'frying_(food).csv', 'category': 'Frying_(food)'},
    {'filename': 'toilet_flush.csv', 'category': 'Toilet_flush'},
    {'filename': 'bathtub.csv', 'category': 'Bathtub_(filling_or_washing)'},
    #{'filename':'','category':''},
]

exclude_filter = []
for className in classes:
    with open("filters/" + className['filename'], newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            exclude_filter.append([row[4].split('/')[-1], 'FSD50k', className['category']])

with open("filters/exclude_files_filter.csv", 'a', newline='') as file:
    writer = csv.writer(file)
    for filter in exclude_filter:
        writer.writerow(filter)
