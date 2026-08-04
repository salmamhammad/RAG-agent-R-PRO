# FastAPI приложение
import logging
import sys
import io
from fastapi import FastAPI, HTTPException, Request
from backend.exceptions import RateLimitExceeded

from fastapi.middleware.cors import CORSMiddleware
from backend.models import ChatRequest, ChatResponse, FeedbackRequest,FeedbackResponse, EngineerResponse,CloseTicketRequest
from backend.rag_engine import RAGEngine
from backend.utils import setup_logging, get_logger, now_iso 
from backend.feedback_db import (
    init_db, count_dislikes, get_pending_ticket, get_answered_ticket,
    create_ticket,update_ticket, get_pending_tickets, answer_ticket, get_ticket,get_all_tickets,
    close_ticket, add_user_message_to_ticket, add_assistant_message_to_ticket
)
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from backend.security import RateLimiter, sanitize_input, get_client_ip
import os 
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
# Загружаем переменные окружения 
load_dotenv()

# Настраиваем логирование
setup_logging(log_file="logs/app.log", level=logging.INFO)
logger = get_logger(__name__)  

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/widget", StaticFiles(directory="widget/dist"), name="widget")
app.mount("/images", StaticFiles(directory="data/images"), name="images")

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
init_db()

# Безопасность: ограничитель скорости
rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", 30))
rate_limiter = RateLimiter(requests_per_minute=rate_limit_per_minute)
max_input_length = int(os.getenv("MAX_INPUT_LENGTH", 500))

# Безопасность: ограничитель скорости
rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", 30))
rate_limiter = RateLimiter(requests_per_minute=rate_limit_per_minute)
max_input_length = int(os.getenv("MAX_INPUT_LENGTH", 500))

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    # 1. Ограничение скорости
    client_ip = get_client_ip(req)
    if not rate_limiter.is_allowed(client_ip):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")

    # 2.Длина входного сигнала и защита от инжекции
    is_valid, error_msg = sanitize_input(request.question, max_length=max_input_length)
    if not is_valid:
        logger.warning(f"Invalid input from {client_ip}: {error_msg}")
        
        raise HTTPException(status_code=400, detail=error_msg)
async def chat(request: ChatRequest, req: Request):
    # 1. Ограничение скорости
    client_ip = get_client_ip(req)
    if not rate_limiter.is_allowed(client_ip):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")

    # 2.Длина входного сигнала и защита от инжекции
    is_valid, error_msg = sanitize_input(request.question, max_length=max_input_length)
    if not is_valid:
        logger.warning(f"Invalid input from {client_ip}: {error_msg}")
        
        raise HTTPException(status_code=400, detail=error_msg)
    logger.info(f"Новый запрос: {request.question[:100]}...")
    try:
        ####1##
        ticket_id = None
        if request.ticketId:
           ticket = get_ticket(request.ticketId)
           if ticket and ticket["status"] != "closed":
               add_user_message_to_ticket(request.ticketId, request.question)
        # Проверяем, есть ли уже готовый ответ инженера на этот вопрос
        answered_ticket = get_answered_ticket(request.question)
        if answered_ticket:
            # Если инженер уже ответил, возвращаем его ответ
            engineer_answer = answered_ticket["answer"]
            return ChatResponse(answer=engineer_answer, sources=[])
        start = now_iso()
        result = rag.answer(request.question, history=request.history)
        end = now_iso()
        logger.info(f"Ответ отправлен, длина: {len(result['answer'])}")
        logger.info(f"Ответ отправлен, длина images: {len(result['images'])}")
        logger.info(f"Обработано за {end} - {start}")
        logger.info(f"result : {result['has_context']}")
        if not result["has_context"]:
            if request.ticketId:
                ticket_id = update_ticket(request.ticketId, request.question, request.history)
                logger.info(f"Создан  тикет #{ticket_id} для вопроса без контекста")
            else:
                ticket_id = create_ticket(request.question, request.history)
                logger.info(f"Использаван  тикет #{ticket_id} для вопроса без контекста")
        add_assistant_message_to_ticket(request.ticketId, result["answer"])
        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"],
            images=result["images"],
            ticket_id=ticket_id,
             think=result.get("think") 
        )
    except RateLimitExceeded as e:
        logger.warning(f"Rate limit exceeded for IP {client_ip}: {e}")
        raise HTTPException(status_code=429, detail="Превышен лимит запросов к LLM. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback", response_model=FeedbackResponse)
async def feedback(fb: FeedbackRequest):
    logger.info(f"обратная связь : {fb.question[:100]}...")
    conn = sqlite3.connect("logs/feedback.db")
    c = conn.cursor()
    c.execute("INSERT INTO feedback (question, answer, rating, comment, timestamp) VALUES (?, ?, ?, ?, ?)",
              (fb.question, fb.answer, fb.rating, fb.comment, datetime.now()))
    conn.commit()
    conn.close()
    ###2##
    # Если дизлайк (rating == -1), проверяем количество дизлайков
    ticket_id = None
    if fb.rating == -1:
        dislikes = count_dislikes(fb.question)
        logger.info(f"Дизлайков на вопрос '{fb.question[:50]}': {dislikes}")
        # Проверяем, есть ли уже тикет (pending или answered)
        pending = get_pending_ticket(fb.question)
        answered = get_answered_ticket(fb.question)
        if not pending and not answered and dislikes >= 3:
            # Создаём тикет
            if fb.ticketId:
                ticket_id=update_ticket(fb.ticketId, fb.question, fb.history)
                logger.info(f"обновление тикет #{ticket_id} для вопроса: {fb.question[:50]}...")
            else:
                ticket_id = create_ticket(fb.question, fb.history)
                logger.info(f"Создан тикет #{ticket_id} для вопроса: {fb.question[:50]}...")
            
            ####3## WebSocket -  отправить уведомление инженеру 
        else:
            if pending:
                logger.info(f"Уже есть открытый тикет #{pending['id']} для этого вопроса")
            elif answered:
                logger.info(f"Вопрос уже закрыт в тикете #{answered['id']}")
            elif dislikes < 3:
                logger.info(f"Недостаточно дизлайков: {dislikes}/3")
    logger.info(f"Создан тикет #{ticket_id} ")
    return FeedbackResponse(status="ok", ticket_id=ticket_id)
    
    

@app.get("/engineer/tickets")
async def list_pending_tickets():
    """Возвращает все ожидающие тикеты."""
    tickets = get_pending_tickets()
    return [dict(ticket) for ticket in tickets]

@app.post("/engineer/respond")
async def engineer_respond(payload: EngineerResponse):
    ticket_id = payload.ticket_id
    answer = payload.answer
    logger.info(f"Инженер отвечает на тикет #{ticket_id}")
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket["status"] == "closed":
        raise HTTPException(status_code=400, detail="Ticket already closed")
    answer_ticket(ticket_id, answer)
    question = ticket["question"]
    doc_text = f"Вопрос: {question}\nОтвет: {answer}"
    rag.add_document(doc_text, metadata={"source": "engineer_response", "ticket_id": ticket_id})
    logger.info(f"Инженер ответил на тикет #{ticket_id}")
    return {"status": "ok", "message": "Ответ сохранён и добавлен в базу знаний"}

@app.post("/engineer/close-ticket")
async def close_ticket_endpoint(payload: CloseTicketRequest):
    ticket_id = payload.ticket_id
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket["status"] == "closed":
        raise HTTPException(status_code=400, detail="Ticket already closed")
    close_ticket(ticket_id)
    logger.info(f"Тикет #{ticket_id} закрыт")
    return {"status": "ok"}

@app.get("/ticket/{ticket_id}")
async def get_ticket_status(ticket_id: int):
    """Проверяет статус тикета."""
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return dict(ticket)

# ---- Для уведомлений инженера (простой опрос) ----
@app.get("/engineer/notifications")
async def get_notifications():
    """Возвращает количество ожидающих тикетов (для отображения бейджа)."""
    tickets = get_pending_tickets()
    return {"count": len(tickets)}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/engineer/all-tickets")
async def list_all_tickets():
    """Возвращает все тикеты (и pending, и answered)."""
    tickets = get_all_tickets()
    return [dict(ticket) for ticket in tickets]