import requests

url = 'http://<your_home_assistant_url>/api/states/<your_entity_id>'
headers = {
    'Authorization': 'Bearer <your_long_lived_access_token>',
    'Content-Type': 'application/json'
}


def update_label_value(new_value):
    data = {
        'state': str(new_value)
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print('Label value updated successfully.')
    else:
        print('Failed to update label value:', response.text)
