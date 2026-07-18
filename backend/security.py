# backend/security.py
import time
import re
from collections import defaultdict
from typing import Tuple
import os

# ============================================================
# Ограничитель скорости
# ============================================================
class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # seconds
        self.requests = defaultdict(list)  # IP -> list 

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        # Удалить старые записи за пределами окна
        self.requests[client_ip] = [t for t in self.requests[client_ip] if now - t < self.window_size]
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            return False
        self.requests[client_ip].append(now)
        return True

# ============================================================
# Схемы защиты от быстрого впрыска
# ============================================================
INJECTION_PATTERNS = [
    r'(?i)ignore (?:previous|all|the) (?:instructions|prompt|system prompt)',
    r'(?i)you are now (?:a|an) (?:new|different) (?:assistant|system|ai)',
    r'(?i)system prompt',
    r'(?i)new instruction',
    r'(?i)override',
    r'(?i)disregard',
    r'(?i)you must (?:now|instead)',
    r'(?i)do not (?:follow|obey)',
    r'(?i)change your (?:role|behavior|persona)',
    r'(?i)act as (?:if|though)',
]

def sanitize_input(text: str, max_length: int = 500) -> Tuple[bool, str]:
 
    if not text:
        return False, "Входные данные не могут быть пустыми."
    if len(text) > max_length:
        return False, f"Входные данные превышают максимальную длину в {max_length} символов."
    # Проверить схему инъекций
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text):
            return False, "Введенные данные содержат недопустимый контент."
    return True, ""

def get_client_ip(request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host