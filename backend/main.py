# FastAPI приложение
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.models import ChatRequest, ChatResponse, FeedbackRequest
from backend.rag_engine import RAGEngine
from backend.utils import setup_logging, get_logger, now_iso 
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения 
load_dotenv()

# Настраиваем логирование
setup_logging(log_file="logs/app.log", level=logging.INFO)
logger = get_logger(__name__)  

app = FastAPI()

# CORS для виджета
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация RAG-движка
rag = RAGEngine()

# Инициализация SQLite для фидбэка
def init_db():
    conn = sqlite3.connect("logs/feedback.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS feedback
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  question TEXT, answer TEXT, rating INTEGER,
                  comment TEXT, timestamp DATETIME)""")
    conn.commit()
    conn.close()
init_db()

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    logger.info(f"Новый запрос: {request.question[:100]}...")
    try:
        start = now_iso()
        result = rag.answer(request.question, history=request.history)
        end = now_iso()
        logger.info(f"Ответ отправлен, длина: {len(result['answer'])}")
        logger.info(f"Обработано за {end} - {start}")
        return ChatResponse(**result)
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
async def feedback(fb: FeedbackRequest):
    logger.info(f"обратная связь : {fb.question[:100]}...")
    conn = sqlite3.connect("logs/feedback.db")
    c = conn.cursor()
    c.execute("INSERT INTO feedback (question, answer, rating, comment, timestamp) VALUES (?, ?, ?, ?, ?)",
              (fb.question, fb.answer, fb.rating, fb.comment, datetime.now()))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/health")
async def health():
    return {"status": "healthy"}