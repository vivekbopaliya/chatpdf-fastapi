from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class Question(BaseModel):
    question: str
    pdf_id: str

class ChatMessage(BaseModel):
    user: str
    ai: str
    timestamp: str

class ConversationResponse(BaseModel):
    id: str
    pdf_id: str
    conversation: List[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        orm_mode = True