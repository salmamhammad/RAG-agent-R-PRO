# Pydantic схемы
from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    question: str
    history: Optional[List[dict]] = []  # [{"role": "user", "content": "..."}]

class ChatResponse(BaseModel):
    answer: str
    sources: List[dict]

class FeedbackRequest(BaseModel):
    question: str
    answer: str
    rating: int  # 1 лайк, -1 дизлайк
    comment: Optional[str] = None