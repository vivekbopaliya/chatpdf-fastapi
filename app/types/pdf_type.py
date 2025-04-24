from pydantic import BaseModel
from datetime import datetime

class PDFBase(BaseModel):
    name: str

class PDFResponse(PDFBase):
    id: str
    size: str  
    uploaded_date: datetime
    
    class Config:
        orm_mode = True