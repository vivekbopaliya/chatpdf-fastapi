import uuid
import datetime
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.db import Base

class ChatHistory(Base):
    __tablename__ = "chat_histories"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pdf_id = Column(String, ForeignKey("pdfs.id", ondelete="CASCADE"), nullable=False)
    conversation = Column(JSON, nullable=False, default=list)  # Store chat history as JSON array
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    
    # Relationship with PDF
    pdf = relationship("PDF", back_populates="chat_histories")