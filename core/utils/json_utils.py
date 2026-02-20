import json
import os
from datetime import datetime

def ensure_directory(path):
    os.makedirs(path, exist_ok=True)

def save_json_entry(base_dir, user_id, emotion_data):
    date_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"user_{user_id}_{date_str}.json"
    filepath = os.path.join(base_dir, filename)

    ensure_directory(base_dir)

    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = []

    data.append(emotion_data)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)