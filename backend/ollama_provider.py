import os
from dotenv import load_dotenv

import requests
from typing import List, Dict
from backend.llm_provider import LLMProvider
# Загружаем переменные окружения 
load_dotenv()

class OllamaProvider(LLMProvider):
    def __init__(self, model: str = None, temperature: float = 0.3, max_tokens: int = 2048):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:8000")
        self.model = model or os.getenv("OLLAMA_MODEL", "dengcao/Qwen3-32B:Q5_K_M")
        self.temperature = temperature
        self.max_tokens = max_tokens

    def generate(self, messages: List[Dict[str, str]], **kwargs) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", self.max_tokens)
            }
        }
        response = requests.post(url, json=payload, timeout=300)
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]