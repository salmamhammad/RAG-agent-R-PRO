# Pydantic схемы
from pydantic import BaseModel
from typing import List, Optional,Dict

class ChatRequest(BaseModel):
    question: str
    history: Optional[List[dict]] = []  # [{"role": "user", "content": "..."}]
    ticketId: Optional[int] = None
    
class ChatResponse(BaseModel):
    answer: str
    sources: List[dict]
    images: List[str] = [] 
    ticket_id: Optional[int] = None

class FeedbackRequest(BaseModel):
    question: str
    answer: str
    rating: int  # 1 лайк, -1 дизлайк
    comment: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = None 
    ticketId: Optional[int] = None
class FeedbackResponse(BaseModel):
    status: str
    ticket_id: Optional[int] = None 
    
class EngineerResponse(BaseModel):
    ticket_id: int
    answer: str
class CloseTicketRequest(BaseModel):
    ticket_id: int