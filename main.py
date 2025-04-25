
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import pdf_route, chat_route, auth_route
from app.db import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for chatting with PDF documents",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth_route.router, prefix=settings.API_V1_STR)
app.include_router(pdf_route.router, prefix=settings.API_V1_STR)
app.include_router(chat_route.router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": "Welcome to Chat-PDF!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)