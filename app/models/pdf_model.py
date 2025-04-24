import uuid
import datetime
from sqlalchemy import Column, String, Integer, DateTime, LargeBinary, ForeignKey
from sqlalchemy.orm import relationship

from app.db import Base

class PDF(Base):
    __tablename__ = "pdfs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    size = Column(Integer, nullable=False) 
    uploaded_date = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    content = Column(LargeBinary, nullable=False)  
    
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    chat_histories = relationship("ChatHistory", back_populates="pdf", cascade="all, delete-orphan")
    user = relationship("User", back_populates="pdfs")