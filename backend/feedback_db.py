# backend/feedback_db.py
import sqlite3
from datetime import datetime
import json
import logging
import re
from backend.utils import setup_logging, get_logger, now_iso 

DB_PATH = "logs/feedback.db"
# Настраиваем логирование
setup_logging(log_file="logs/app.log", level=logging.INFO)
logger = get_logger(__name__)  

def normalize(text: str) -> str:
    """Приводит текст к нормализованному виду для сравнения."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)  # удаляем знаки препинания
    text = re.sub(r'\s+', ' ', text)     # заменяем множественные пробелы на один
    return text
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()

     # Создаём таблицу tickets
    c.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            normalized_question TEXT NOT NULL,
            answer TEXT,
            history TEXT,  
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Создаём таблицу feedback
    c.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            answer TEXT,
            rating INTEGER,
            comment TEXT,
            timestamp DATETIME
        )
    """)
    # Добавляем индекс для быстрого поиска по вопросу
    c.execute("CREATE INDEX IF NOT EXISTS idx_tickets_question ON tickets(question)")
    conn.commit()
    conn.close()

def count_dislikes(question: str) -> int:
    """Считает количество дизлайков для данного вопроса."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM feedback WHERE question = ? AND rating = -1", (question,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_pending_ticket(question: str):
    """Возвращает тикет со статусом 'pending' для данного вопроса, если есть."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM tickets WHERE question = ? AND status = 'pending'", (question,))
    ticket = c.fetchone()
    conn.close()
    return ticket

def get_answered_ticket(question: str):
    norm = normalize(question)
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM tickets WHERE normalized_question = ? AND status = 'closed'", (norm,))
    ticket = c.fetchone()
    conn.close()
    return ticket

def create_ticket(question: str, history: list = None) -> int:
    norm = normalize(question)
    conn = get_db_connection()
    c = conn.cursor()
    history_json = json.dumps(history) if history else None
    c.execute("INSERT INTO tickets (question, normalized_question, history, status) VALUES (?, ?, ?, 'pending')",
              (question, norm, history_json))
    ticket_id = c.lastrowid
    conn.commit()
    conn.close()
    print(f"[DB] Создан тикет #{ticket_id} для нормализованного вопроса: {norm}")
    return ticket_id

def update_ticket(ticket_id: int, question: str, history: list = None) -> int:
    norm = normalize(question)
    conn = get_db_connection()
    c = conn.cursor()
    history_json = json.dumps(history) if history else None
    c.execute(
        "UPDATE tickets SET question = ?, normalized_question = ?, history = ?, status = 'pending' WHERE id = ?",
        (question, norm, history_json, ticket_id)
    )
    conn.commit()
    conn.close()
    logger.info(f"[DB] обновлен тикет #{ticket_id} для нормализованного вопроса: {norm}")
    return ticket_id

def get_pending_tickets() -> list:
    """Возвращает все тикеты со статусом 'pending'."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM tickets WHERE status = 'pending' ORDER BY created_at ASC")
    tickets = c.fetchall()
    conn.close()
    return tickets


def answer_ticket(ticket_id: int, answer: str):
    conn = get_db_connection()
    c = conn.cursor()
    ticket = get_ticket(ticket_id)
    if not ticket:
        return
    history = json.loads(ticket['history']) if ticket['history'] else []
    history.append({"role": "assistant", "content": answer})
    history_json = json.dumps(history)
    # Если статус был 'pending', меняем на 'in_progress'
    new_status = 'in_progress' if ticket['status'] == 'pending' else ticket['status']
    c.execute("UPDATE tickets SET answer = ?, history = ?, status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
              (answer, history_json, new_status, ticket_id))
    conn.commit()
    conn.close()

def close_ticket(ticket_id: int):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE tickets SET status = 'closed', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (ticket_id,))
    conn.commit()
    conn.close()

def add_user_message_to_ticket(ticket_id: int, message: str):
    conn = get_db_connection()
    c = conn.cursor()
    ticket = get_ticket(ticket_id)
    if not ticket:
        return
    history = json.loads(ticket['history']) if ticket['history'] else []
    history.append({"role": "user", "content": message})
    c.execute("UPDATE tickets SET history = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
              (json.dumps(history), ticket_id))
    conn.commit()
    conn.close()

def add_assistant_message_to_ticket(ticket_id: int, message: str):
    conn = get_db_connection()
    c = conn.cursor()
    ticket = get_ticket(ticket_id)
    if not ticket:
        return
    history = json.loads(ticket['history']) if ticket['history'] else []
    history.append({"role": "assistant", "content": message})
    c.execute("UPDATE tickets SET history = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
              (json.dumps(history), ticket_id))
    conn.commit()
    conn.close()
    
def get_ticket(ticket_id: int):
    """Возвращает тикет по ID."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    ticket = c.fetchone()
    conn.close()
    return ticket

def get_all_tickets() -> list:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM tickets ORDER BY created_at DESC")
    tickets = c.fetchall()
    conn.close()
    return tickets


def get_pending_tickets() -> list:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM tickets WHERE status = 'pending' or status = 'in_progress' ORDER BY created_at ASC")
    tickets = c.fetchall()
    conn.close()
    return tickets