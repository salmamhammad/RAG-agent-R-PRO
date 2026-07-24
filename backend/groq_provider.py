# реализация Groq
import os
from dotenv import load_dotenv

from groq import Groq
from backend.llm_provider import LLMProvider
from typing import List, Dict
# Загружаем переменные окружения 
load_dotenv()


class GroqProvider(LLMProvider):
    def __init__(self, temperature: float = 0.3, max_tokens: int = 2048):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY не задан. Проверьте .env")
        self.client = Groq(api_key=api_key)
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.temperature = temperature
        self.max_tokens = max_tokens

    def generate(self, messages: List[Dict[str, str]], **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens)
        )
        return response.choices[0].message.content