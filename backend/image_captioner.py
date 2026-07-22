import requests
import base64
import os
from typing import List, Dict

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "llava:13b")  

def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def generate_caption(image_path: str, prompt: str = "Опиши это изображение на русском языке.") -> str:
    """Отправляет изображение в LLaVA и возвращает описание."""
    url = f"{OLLAMA_URL}/api/generate"
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "images": [encode_image_to_base64(image_path)],
        "stream": False
    }
    response = requests.post(url, json=payload, timeout=300)
    response.raise_for_status()
    return response.json().get("response", "").strip()