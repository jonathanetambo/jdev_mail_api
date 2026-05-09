import os
import json

from services.crypto_service import encrypt_data


LOG_DIR = 'logs/encrypted'


os.makedirs(LOG_DIR, exist_ok=True)



def write_log(site_id, log_data):

    filename = f'{site_id}.jdev'

    path = os.path.join(LOG_DIR, filename)

    json_data = json.dumps(log_data)

    encrypted = encrypt_data(json_data)

    with open(path, 'ab') as file:
        file.write(encrypted + b'\n')