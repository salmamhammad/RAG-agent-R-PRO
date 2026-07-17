## AI agent R-PRO

# Предварительные требования
- Python 3.11 или новее (рекомендуется 3.11–3.13)
- Git (для клонирования)
- 7‑Zip (Windows) или p7zip (Linux/macOS) – для распаковки CHM-файлов


# instructions


```
bash
python -m venv venv
.\venv\Scripts\Activate.ps1 // source venv/bin/activate (ubuntu)
pip install --upgrade pip
pip install -r requirements.txt

python -m scripts.run_ingestion
python check_chroma.py // проверить текущие чанки

uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
python -m http.server 3000            

```
страница для чата с ИИ:
http://localhost:3000/test_widget.html

страница для инженерной поддержки:
http://localhost:8000/static/engineer.html

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
GROQ_MODEL= "qwen/qwen3-32b"
LLM_PROVIDER=groq            # groq or ollama
OLLAMA_MODEL= "dengcao/Qwen3-32B:Q5_K_M"
OLLAMA_BASE_URL="http://localhost:8000"

TOP_K=8                    # количество чанков, возвращаемых поиском
EMBEDDING_MODEL=d0rj/e5-small-en-ru   # модель эмбеддингов d0rj/e5-small-en-ru 

LOCAL_MODEL_PATH=F:\rag-support-agent\models\Qwen3-8B
USE_API=true    

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
