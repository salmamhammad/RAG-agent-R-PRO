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
python check_chroma.py // проверить текущие чанки
python -m scripts.run_ingestion // для обучения модели
python test_chat.py
           
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
# GROQ_MODEL= "openai/gpt-oss-120b"
GROQ_MODEL= "qwen/qwen3-32b"


TOP_K=5                      # количество чанков, возвращаемых поиском
LLM_PROVIDER=groq            # пока только groq 
EMBEDDING_MODEL=d0rj/e5-small-en-ru   # модель эмбеддингов

LOCAL_MODEL_PATH=F:\rag-support-agent\models\Qwen3-8B
USE_API=true   

```

# Подготовка данных
Поместите файлы знаний (PDF, TXT, CHM, JSONL) в папки:

- data/docs/ – для основных документов
- data/chm/ – для файлов справки CHM 
- data/jsonl/ – для файлов справки JSONL 