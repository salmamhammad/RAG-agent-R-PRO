# backend/qwen_provider.py
import os
from dotenv import load_dotenv

from typing import List, Dict
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from backend.llm_provider import LLMProvider
# Загружаем переменные окружения 
load_dotenv()

class QwenProvider(LLMProvider):
    def __init__(self, temperature: float = 0.3, max_tokens: int = 512, model_path: str = None):
        self.model_path = model_path or os.getenv("LOCAL_MODEL_PATH", "models/Qwen3-8B")
        self.temperature = temperature
        self.max_tokens = max_tokens

        print(f"Загрузка локальной модели из {self.model_path}...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)

        # Пробуем загрузить с настройками, устойчивыми к недостатку памяти
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                device_map="auto",
                torch_dtype=torch.float16,
                low_cpu_mem_usage=True,
                trust_remote_code=True
            )
        except (ValueError, RuntimeError) as e:
            print(f"Ошибка загрузки с device_map='auto': {e}")
            print("Пытаемся загрузить на CPU в float32...")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                device_map="cpu",
                torch_dtype=torch.float32,
                trust_remote_code=True
            )
        print("Модель загружена.")

    def generate(self, messages: List[Dict[str, str]], **kwargs) -> str:
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=kwargs.get("max_tokens", self.max_tokens),
            temperature=kwargs.get("temperature", self.temperature),
            do_sample=True
        )
        response = self.tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:],
            skip_special_tokens=True
        )
        return response