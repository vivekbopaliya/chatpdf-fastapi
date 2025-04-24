import uuid
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
import datetime

from app.db import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    session_id = Column(String, unique=True, nullable=True)  
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    pdfs = relationship("PDF", back_populates="user", cascade="all, delete-orphan")