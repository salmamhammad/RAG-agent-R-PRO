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
npm install
npm run build
python -m scripts.run_ingestion


uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
python -m http  server 3000            
```

# Установка chmlib или p7zip
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
# Выбор провайдера: true = Groq API, false = локальная модель (Transformers)
USE_API=true

# Groq (если USE_API=true)
GROQ_API_KEY=ваш_ключ_здесь
GROQ_MODEL=llama-3.1-8b-instant

# Локальная модель (если USE_API=false)
LOCAL_MODEL_PATH=models/Qwen3-8B

# Параметры RAG
TOP_K=5
EMBEDDING_MODEL=d0rj/e5-small-en-ru
```

# Подготовка данных
Поместите файлы знаний (PDF, TXT, CHM, JSONL) в папки:

- data/docs/ – для основных документов
- data/chm/ – для файлов справки CHM 
- data/jsonl/ – для файлов справки JSONL 