# backend/__init__.py

from .chroma_client import get_vector_store
from .groq_provider import GroqProvider
from .llm_provider import LLMProvider
from .models import ChatRequest, ChatResponse, FeedbackRequest,FeedbackResponse, EngineerResponse,CloseTicketRequest
from .rag_engine import RAGEngine
from .utils import setup_logging, get_logger, truncate_text, clean_text, format_sources, safe_json_serialize, now_iso,contains_unknown_phrase, parse_response
from .feedback_db import get_db_connection, init_db, count_dislikes, get_pending_ticket, get_answered_ticket, create_ticket,update_ticket, get_pending_tickets, answer_ticket, get_ticket,get_all_tickets,close_ticket,add_user_message_to_ticket, add_assistant_message_to_ticket
from .image_captioner import generate_caption
from .exceptions import RateLimitExceeded


__all__ = [
    'get_vector_store',
    'GroqProvider',
    'LLMProvider',
    'ChatRequest',
    'ChatResponse',
    'FeedbackRequest',
    'FeedbackResponse',
    'EngineerResponse',
    'CloseTicketRequest',
    'RAGEngine',
    'setup_logging',
    'get_logger',
    'truncate_text',
    'clean_text',
    'format_sources',
    'safe_json_serialize',
    'now_iso',
    'contains_unknown_phrase',
    'parse_response',
    'get_db_connection',
    'init_db',
    'count_dislikes',
    'get_pending_ticket',
    'get_answered_ticket',
    'create_ticket',
    'update_ticket',
    'get_pending_tickets',
    'answer_ticket',
    'get_ticket',
    'get_all_tickets',
    'close_ticket',
    'add_user_message_to_ticket',
    'add_assistant_message_to_ticket',
    'generate_caption',
    'RateLimitExceeded'
    
    
    
    
]