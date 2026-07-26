## AI agent R-PRO

# Предварительные требования
- Python 3.11 или новее (рекомендуется 3.11–3.13)
- Git (для клонирования)
- 7‑Zip (Windows) или p7zip (Linux/macOS) – для распаковки CHM-файлов


# instructions

## для обучения модели
### 1.  если обучение с использованием изображений
```
bash
docker-compose build --no-cache ollama
docker-compose up ollama
docker-compose exec ollama ollama pull llava
```
В файле .env параметр PROCESS_IMAGES должен быть установлен в значение true.
```
bash
python -m venv venv
.\venv\Scripts\Activate.ps1 // source venv/bin/activate (ubuntu)
pip install --upgrade pip
pip install -r requirements.txt

python -m scripts.run_ingestion

uvicorn backend.main:app  --host 0.0.0.0 --port 8000
python -m http.server 3000            

```

### 2. Если обучение проходит без изображений
В файле .env параметр PROCESS_IMAGES должен быть установлен в значение false.

```
bash
python -m venv venv
.\venv\Scripts\Activate.ps1 // source venv/bin/activate (ubuntu)
pip install --upgrade pip
pip install -r requirements.txt

python -m scripts.run_ingestion

uvicorn backend.main:app  --host 0.0.0.0 --port 8000
python -m http.server 3000            

```

## для открытия страницы тестирования ИИ-агента

```
bash

.\venv\Scripts\Activate.ps1 // source venv/bin/activate (ubuntu)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
python -m http.server 3000            

```
страница для чата с ИИ:
http://localhost:3000/test_widget.html

страница для инженерной поддержки:
http://localhost:8000/static/engineer.html

# работа с Docker
Существует возможность запустить весь проект в Docker, используя два контейнера: бэкенд и Ollama. Однако этот вариант требует значительных ресурсов для работы.
## запустить все контейнеры
```
bash
docker-compose up -d
```
## посмотреть, что оба контейнера работают:
```
bash
docker-compose ps
```
## скачать модель  в контейнер Ollama
```
bash
docker-compose exec ollama ollama pull llava
```
## посмотреть, что модель появилась
```
bash
docker-compose exec ollama ollama list
```

## Проверить доступность Ollama изнутри контейнера backend
```
bash
docker-compose exec backend curl http://ollama:11434/api/tags
```
## запустить индексацию внутри контейнера backend

```
bash
docker-compose exec backend python -m scripts.run_ingestion

```



# Установка chmlib или p7zip
Для работы pychm в некоторых системах требуется библиотека chmlib.
Или используйте p7zip вместо pychm.
Код проверит наличие библиотеки и воспользуется доступной автоматической библиотекой.
Linux (Debian/Ubuntu):
```
bash
sudo apt-get install libchm-dev
```
Linux (RHEL/CentOS/Fedora):
```
bash
sudo yum install chmlib-devel // или
sudo apt-get install p7zip-full

```
macOS:
```
bash	
brew install chmlib // или
brew install p7zip

```
Windows	Через MSYS2: 
```
bash
pacman -S mingw-w64-ucrt-x86_64-chmlib 
```
 или через Cygwin
 или 7-Zip installer for Windows

# .env
```
bash
GROQ_API_KEY= "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"
# GROQ_MODEL= "openai/gpt-oss-120b"  "qwen/qwen3-32b" "mixtral-8x7b-32768"
GROQ_MODEL= "qwen/qwen3.6-27b"   #для логических ответов
LLM_PROVIDER=groq            # groq or ollama
OLLAMA_BASE_URL= http://ollama:11434  #http://localhost:11434  # docker: http://ollama:11434
OLLAMA_MODEL=qwen3.6  

TOP_K=3                    # количество чанков, возвращаемых поиском
EMBEDDING_MODEL=intfloat/multilingual-e5-small  # модель эмбеддингов d0rj/e5-small-en-ru 
IMAGES_OLLAMA_BASE_URL= http://localhost:11434  #http://localhost:11434  # docker: http://ollama:11434
IMAGES_OLLAMA_MODEL=llava  # llava:13b
PROCESS_IMAGES=true
LOCAL_MODEL_PATH=F:\rag-support-agent\models\Qwen3-8B
USE_API=true   

# Настройки безопасности
RATE_LIMIT_PER_MINUTE=30
MAX_INPUT_LENGTH=500

#папки данных
DATA_DOCS="data/docs"
DATA_CHM="data/chm"
DATA_JSONL="data/jsonl"
DATA_FAQ='data/faq'
DATA_IMAGE="data/images" 
DATA_HTML="data/chm_html"


ANONYMIZED_TELEMETRY=false
FORBIDDEN_TERMS=ISimPlugin, AddComponent, RemoveComponent, XAML, SimLab.Application, ISimComponent, CreateComponent
```
# тестирования
```
bash
# 1. Провести полную оценку
python tests/evaluate_full.py

# 2. запустить диагностику
python tests/diagnose.py

# 3. Проведение исследования абляции (трудоемкий процесс)
python tests/ablation.py

# 4.Просмотреть результаты
cat tests/detailed_results.json

```
## Интерпретация метрик

| Metric | Good Score | Okay Score | Poor Score |
|--------|------------|------------|------------|
| ROUGE-L | > 0.6 | 0.4 - 0.6 | < 0.4 |
| Hit Rate | > 80% | 50% - 80% | < 50% |
| Semantic Similarity | > 0.8 | 0.6 - 0.8 | < 0.6 |
| Faithfulness | > 0.8 | 0.6 - 0.8 | < 0.6 |
| Latency | < 2000 ms | 2000 - 5000 ms | > 5000 ms |
| Success Rate | > 95% | 90% - 95% | < 90% |

# Подготовка данных
Поместите файлы знаний (PDF, TXT, CHM, JSONL) в папки:

- data/docs/ – для основных документов
- data/chm/ – для файлов справки CHM 
- data/jsonl/ – для файлов справки JSONL 
- data/faq/ - JSON-файл с вопросами и ответами,  Ожидает структуру: { "faq": [ { "category": "...", "question": "...", "answer": "..." } ] }

