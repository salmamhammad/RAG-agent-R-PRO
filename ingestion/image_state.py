import os
import json
import hashlib
from datetime import datetime

IMAGE_STATE_FILE = "image_state.json"

def get_image_hash(image_path: str) -> str:
    """Вычисляет SHA-256 хеш содержимого файла изображения."""
    hasher = hashlib.sha256()
    with open(image_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def load_image_state() -> dict:
    """Загружает состояние изображений из JSON-файла."""
    if os.path.exists(IMAGE_STATE_FILE):
        with open(IMAGE_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_image_state(state: dict):
    """Сохраняет состояние изображений в JSON-файл."""
    with open(IMAGE_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def should_process_image(image_path: str, state: dict) -> bool:
    """
    Проверяет, нужно ли обрабатывать изображение.
    Возвращает True, если файла нет в состоянии или хеш изменился.
    """
    if image_path not in state:
        return True
    current_hash = get_image_hash(image_path)
    if state[image_path].get("hash") != current_hash:
        return True
    return False