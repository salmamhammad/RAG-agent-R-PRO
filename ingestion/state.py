# ingestion/state.py
import os
import json
import hashlib

STATE_FILE = "ingestion_state.json"

def get_file_hash(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def get_files_state(root_dirs: list) -> dict:
    """
    Собирает состояние всех поддерживаемых файлов из нескольких корневых папок.
    Ключом словаря является относительный путь от корня проекта.
    """
    state = {}
    extensions = (".pdf", ".txt",".chm")
    
    for root_dir in root_dirs:
        if not os.path.exists(root_dir):
            continue
        for dirpath, _, filenames in os.walk(root_dir):
            for file in filenames:
                if file.lower().endswith(extensions):
                    full_path = os.path.join(dirpath, file)
                    # Относительный путь от корня проекта (для уникальности)
                    rel_path = os.path.relpath(full_path, start=".")
                    stat = os.stat(full_path)
                    state[rel_path] = {
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                        "hash": get_file_hash(full_path)
                    }
    return state

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)