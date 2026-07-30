# реализация Groq
import os
from dotenv import load_dotenv
import time
from groq import Groq , GroqError
from backend.llm_provider import LLMProvider
from backend.exceptions import RateLimitExceeded

from typing import List, Dict
# Загружаем переменные окружения 
load_dotenv()


class GroqProvider(LLMProvider):
    def __init__(self, temperature: float = 0.3, max_tokens: int = 3072):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY не задан. Проверьте .env")
        self.client = Groq(api_key=api_key)
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.temperature =  float(os.getenv("LLM_TEMPERATURE", temperature))
        self.max_tokens = max_tokens
        self.max_retries = int(os.getenv("GROQ_MAX_RETRIES", "3"))
        self.retry_delay = int(os.getenv("GROQ_RETRY_DELAY", "1"))
    
    def generate(self, messages: List[Dict[str, str]], **kwargs) -> str:
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=kwargs.get("temperature", self.temperature),
                    max_tokens=kwargs.get("max_tokens", self.max_tokens)
                )
                return response.choices[0].message.content
            except GroqError as e:
                # Проверяем, является ли ошибка превышением лимита (код 429)
                status_code = getattr(e, 'status_code', None)
                if status_code == 429:
                    if attempt < self.max_retries - 1:
                        # Экспоненциальная задержка: 1, 2, 4... секунд
                        sleep_time = self.retry_delay * (2 ** attempt)
                        time.sleep(sleep_time)
                        continue
                    else:
                        # Все попытки исчерпаны
                        raise RateLimitExceeded("Groq API rate limit exceeded after retries") from e
                # Другие ошибки пробрасываем дальше
                raise
        # Если цикл завершился без return (защита)
        raise RateLimitExceeded("Groq API rate limit exceeded")