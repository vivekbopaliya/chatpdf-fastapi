import os
from dotenv import load_dotenv

load_dotenv()

class Settings():
    PROJECT_NAME: str = "ChatPDF API"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "5f8c7e0a8cb9dca13d6f0d37e9d54f1e8c5c0f6bca9d1c8a3e6f0c9d3e9c1a5b")
    ALGORITHM: str = "HS256"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost/chatpdf")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    
    class Config:
        case_sensitive = True

settings = Settings()