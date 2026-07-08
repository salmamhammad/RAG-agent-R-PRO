import os
from dotenv import load_dotenv
from backend.rag_engine import RAGEngine

load_dotenv()

def clean_response(text: str) -> str:
    """Удаляет служебный маркер [NO_CONTEXT] из ответа."""
    return text.replace("[NO_CONTEXT]", "").strip()

def main():
    print("\n Добро пожаловать в чат-агент поддержки Р-Про!")
    print("Введите ваш вопрос (или 'exit' / 'выход' для завершения):")
    print("-" * 60)

    # Инициализация движка (можно указать другую модель, если нужно)
    rag = RAGEngine()
    print(f"Количество чанков в базе: {rag.count_chunks()}")
    history = []  # список сообщений для контекста

    while True:
        user_input = input("\n Вы: ").strip()

        # Команды выхода
        if user_input.lower() in ("exit", "quit", "выход", "пока", "q"):
            print(" До свидания! Всегда рады помочь.")
            break

        if not user_input:
            continue

        # Получение ответа от агента
        result = rag.answer(user_input, history=history)
        raw_answer = result.get("answer", "")
        clean_answer = clean_response(raw_answer)
        sources = result.get("sources", [])

        # Вывод ответа
        print(f" Агент: {clean_answer}")
        if sources:
            print(f"    Использовано источников: {len(sources)}")

        # Сохраняем диалог в историю (сырой ответ с маркером, если он есть)
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": raw_answer})

if __name__ == "__main__":
    main()