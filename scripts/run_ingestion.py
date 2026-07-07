# скрипт для запуска индексации
"""
Скрипт для запуска индексации базы знаний.
Загружает документы из папки data/docs/, разбивает на чанки,
вычисляет эмбеддинги и сохраняет в ChromaDB.
Запуск: python -m scripts.run_ingestion
"""

import sys
import os
from pathlib import Path

# Добавляем корень проекта в sys.path, чтобы импортировать модули
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from ingestion.indexer import build_index

def main():
    print(" Запуск индексации базы знаний...")
    
    # Проверяем, есть ли данные для индексации
    data_dir = ROOT_DIR / "data" / "docs"
    if not data_dir.exists():
        print(f"  Папка с данными не найдена: {data_dir}")
        print("   Создайте папку data/docs/ и поместите туда PDF или текстовые файлы.")
        sys.exit(1)
    
    files = list(data_dir.glob("*"))
    if not files:
        print(f"  Папка {data_dir} пуста. Добавьте документы.")
        sys.exit(1)
    
    try:
        build_index()
        print(" Индексация успешно завершена.")
        print(f"   Векторная база данных сохранена в chroma_db/")
    except Exception as e:
        print(f" Ошибка при индексации: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()