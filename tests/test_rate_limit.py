# tests/test_rate_limit.py
import requests
import time
import json
import sys
import os

API_URL = "http://localhost:8000/chat"
REQUEST_COUNT = 35  # Больше лимита (30)

def load_questions_from_json(file_path: str):
    """Загружает вопросы из JSON-файла с тестовыми вопросами."""
    if not os.path.exists(file_path):
        print(f"Файл {file_path} не найден. Используем заглушку.")
        return [f"Тестовый вопрос #{i}" for i in range(1, 11)]

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Ожидаем список объектов с ключом "query"
    if isinstance(data, list):
        questions = [item.get("query", "Вопрос не найден") for item in data if "query" in item]
    elif isinstance(data, dict) and "faq" in data:
        questions = [item.get("question", "Вопрос не найден") for item in data["faq"] if "question" in item]
    else:
        questions = [f"Тестовый вопрос #{i}" for i in range(1, 11)]

    if not questions:
        questions = ["Как сбросить пароль?"] * 10

    return questions

def test_rate_limit():
    # Загружаем вопросы
    questions = load_questions_from_json("tests/test_questions_faq.json")
    print(f"Загружено {len(questions)} уникальных вопросов.")

    print(f"Отправка {REQUEST_COUNT} запросов на {API_URL}...")
    responses = []
    start_time = time.time()

    for i in range(1, REQUEST_COUNT + 1):
        # Берем вопрос по кругу
        question = questions[(i - 1) % len(questions)]
        payload = {"question": question, "history": []}
        try:
            resp = requests.post(API_URL, json=payload, timeout=5)
            status = resp.status_code
            responses.append(status)
            print(f"Запрос {i}: статус {status}")
        except requests.exceptions.RequestException as e:
            print(f"Запрос {i}: ошибка - {e}")
            responses.append("error")

        # Небольшая задержка (можно убрать для более агрессивного теста)
        # time.sleep(0.05)

    elapsed = time.time() - start_time
    print(f"\nВсего отправлено: {len(responses)}")
    print(f"Время выполнения: {elapsed:.2f} сек")

    # Подсчёт статусов
    status_counts = {}
    for s in responses:
        status_counts[s] = status_counts.get(s, 0) + 1

    print("Распределение статусов:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")

    # Проверка наличия 429
    if 429 in status_counts:
        print("\n Rate limiting работает: получен ответ 429 Too Many Requests")
    else:
        print("\n Rate limiting не сработал: ответ 429 не получен")

if __name__ == "__main__":
    test_rate_limit()