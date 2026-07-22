#!/bin/sh
set -e

echo "🔍 Проверка базы данных ChromaDB..."

# Проверяем, существует ли папка chroma_db и есть ли в ней файлы
if [ ! -d "chroma_db" ] || [ -z "$(ls -A chroma_db 2>/dev/null)" ]; then
    echo "📦 База данных не найдена или пуста. Запускаем индексацию..."
    python -m scripts.run_ingestion
else
    echo "✅ База данных уже существует."
fi

echo "🚀 Запуск бэкенда..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000