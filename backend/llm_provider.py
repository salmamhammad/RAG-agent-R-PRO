# backend/llm_provider.py
import os
from abc import ABC, abstractmethod
from typing import List, Dict

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, messages: List[Dict[str, str]], **kwargs) -> str:
        pass

def get_llm_provider(**kwargs):
    """
    Фабрика создаёт провайдера в зависимости от переменной USE_API.
    Если USE_API=true (по умолчанию) – используем Groq.
    Если false – загружаем локальную модель из папки, указанной в LOCAL_MODEL_PATH.
    """
    use_api = os.getenv("USE_API", "true").lower() == "true"
    if use_api:
        provider = os.getenv("LLM_PROVIDER", "groq").lower()
        model_name = os.getenv("OLLAMA_MODEL", "dengcao/Qwen3-32B:Q5_K_M").lower()
        if provider == "groq":
           from backend.groq_provider import GroqProvider
           return GroqProvider(**kwargs)
        elif provider == "ollama":
           from backend.ollama_provider import OllamaProvider
           return OllamaProvider(model=model_name, **kwargs)
    else:
        from backend.qwen_provider import QwenProvider
        return QwenProvider(**kwargs)