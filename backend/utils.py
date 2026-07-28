"""
Вспомогательные утилиты для бэкенда:
- настройка логирования
- обработка текста
- форматирование источников
- безопасная работа с данными
"""

import re
import os
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional,  Set, Tuple
from pathlib import Path
import unicodedata

# ---------- Логирование ----------
def setup_logging(log_file: str = "logs/app.log", level: int = logging.INFO) -> None:
    """
    Настраивает логирование в файл и консоль.
    """
    # Создаём папку для логов, если её нет
    log_dir = Path(log_file).parent
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

def get_logger(name: str) -> logging.Logger:
    """Возвращает логгер с заданным именем."""
    return logging.getLogger(name)

# ---------- Обработка текста ----------
def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """
    Обрезает текст до указанной длины и добавляет суффикс, если текст длиннее.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def clean_text(text: str) -> str:
    """
    Удаляет лишние пробелы, управляющие символы и нормализует отступы.
    Можно расширить для удаления служебных токенов.
    """
    # Заменяем множественные пробелы и переводы строк на одиночные
    import re
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ---------- Форматирование источников ----------
def format_sources(sources: List[Dict[str, Any]], max_text_len: int = 150) -> List[Dict[str, Any]]:
    """
    Форматирует список источников для выдачи пользователю.
    Каждый источник содержит текст (обрезанный) и оценку релевантности.
    """
    formatted = []
    for src in sources:
        # Если источник: NodeWithScore из LlamaIndex
        if hasattr(src, 'node'):
            text = src.node.get_content()
            score = src.score
        else:
            # Если это словарь
            text = src.get('text', '')
            score = src.get('score', 0.0)

        formatted.append({
            "text": truncate_text(clean_text(text), max_text_len),
            "score": round(score, 4) if isinstance(score, float) else 0.0
        })
    return formatted

# ---------- Безопасное преобразование ----------
def safe_json_serialize(obj: Any) -> str:
    """
    Безопасно сериализует объект в JSON, игнорируя несериализуемые поля.
    """
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": "Failed to serialize", "detail": str(e)})

# ---------- Работа с временем ----------
def now_iso() -> str:
    """Возвращает текущее время в формате ISO."""
    return datetime.now().isoformat()

# ---------- Проверка наличия ключевых фраз ----------
def contains_unknown_phrase(text: str) -> bool:
    """
    Проверяет, содержит ли ответ фразы, указывающие на отсутствие информации.
    Может использоваться для дополнительного анализа качества ответа.
    """
    phrases = [
        "не знаю",
        "не нашёл",
        "не могу найти",
        "обратитесь к инженеру",
        "информация отсутствует",
        "не удалось найти",
        "не располагаю информацией"
    ]
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in phrases)

def is_greeting_or_small_talk(text: str) -> bool:
    """Check if the user input is a greeting or casual conversation."""
    greetings = [
        "привет", "здравствуй", "здравствуйте", "доброе утро", "добрый день",
        "добрый вечер", "хай", "hello", "hi", "ку", "здарова", "салют",
        "как дела", "как ты", "как жизнь", "как настроение", "что делаешь",
        "спасибо", "благодарю", "merci", "thanks", "thx"
    ]
    text_lower = text.lower().strip()
    return any(greeting in text_lower for greeting in greetings)


def load_forbidden_terms() -> Set[str]:
    """
    Загружает список запрещённых терминов из переменной окружения FORBIDDEN_TERMS.
    Возвращает множество терминов в нижнем регистре.
    """
    terms_str = os.getenv("FORBIDDEN_TERMS", "")
    if not terms_str:
        return set()
    # Разбиваем по запятой, удаляем пробелы, приводим к нижнему регистру
    return {term.strip().lower() for term in terms_str.split(",") if term.strip()}

def contains_forbidden_term(text: str, forbidden_set: Set[str]) -> bool:
    """
    Проверяет, содержит ли текст хотя бы один из запрещённых терминов.
    """
    if not forbidden_set:
        return False
    text_lower = text.lower()
    # Используем границы слов, чтобы не ловить части слов (например, "component" в "component")
    for term in forbidden_set:
        # Ищем как отдельное слово или с учётом регистра
        if re.search(rf'\b{re.escape(term)}\b', text_lower):
            return True
    return False

def is_term_in_context(term: str, context: str) -> bool:
    """
    Проверяет, встречается ли термин в контексте (регистронезависимо).
    """
    return term.lower() in context.lower()



def parse_response(text: str) -> Tuple[str, Optional[str]]:
    """
    Извлекает блок мыслей из ответа модели.
    Возвращает (clean_answer, think_content).
    Если тегов нет, think_content = None.
    """
    # Ищем открывающий тег <think> (с возможными пробелами)
    start_match = re.search(r'<think\s*>', text, re.IGNORECASE)
    if not start_match:
        return text, None
    start_idx = start_match.end()
    
    # Ищем закрывающий тег </think>
    end_match = re.search(r'</think\s*>', text, re.IGNORECASE)
    if end_match:
        # Есть закрывающий
        think_content = text[start_idx:end_match.start()].strip()
        clean_answer = text[:start_match.start()] + text[end_match.end():]
    else:
        # Нет закрывающего – считаем до конца строки
        think_content = text[start_idx:].strip()
        clean_answer = text[:start_match.start()].strip()
    
    return clean_answer.strip(), think_content