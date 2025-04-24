import io
import json
import datetime
from typing import List, Optional
import pickle
import uuid
from pypdf import PdfReader
from dotenv import load_dotenv
import openai
import os
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.llms.openai import OpenAI
from langchain_community.callbacks.manager import get_openai_callback
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from sqlalchemy import create_engine, Column, String, DateTime, Integer, LargeBinary, JSON, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.exc import SQLAlchemyError

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost/chatpdf")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class PDF(Base):
    __tablename__ = "pdfs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    size = Column(Integer, nullable=False)  
    uploaded_date = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    content = Column(LargeBinary, nullable=False)  
    
    chat_histories = relationship("ChatHistory", back_populates="pdf", cascade="all, delete-orphan")

class ChatHistory(Base):
    __tablename__ = "chat_histories"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pdf_id = Column(String, ForeignKey("pdfs.id", ondelete="CASCADE"), nullable=False)
    conversation = Column(JSON, nullable=False, default=list)  
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    
    pdf = relationship("PDF", back_populates="chat_histories")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Bytes to KB conversion for display purposes
def bytes_to_kilobytes(bytes_value):
    return f"{bytes_value / 1024:.2f} KB"

class Question(BaseModel):
    question: str
    pdf_id: str
    conversation_id: Optional[str] = None

class ConversationResponse(BaseModel):
    id: str
    pdf_id: str
    conversation: List[dict]
    created_at: datetime.datetime

class PDFResponse(BaseModel):
    id: str
    name: str
    size: str  
    uploaded_date: datetime.datetime

@app.get('/')
def index():
    return {"msg": 'Chat-PDF API is running'}

@app.post('/upload')
async def pdf_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file:
        raise HTTPException(status_code=400, detail='Please upload a file')
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail='Uploaded file must be a PDF')
    
    try:
        pdf_binary_data = await file.read()
        
        file_size = len(pdf_binary_data)
        
        pdf = io.BytesIO(pdf_binary_data)
        pdf_content = PdfReader(pdf)

        text = ''
        for i in pdf_content.pages:
            text += i.extract_text()

        text_splitter = CharacterTextSplitter(
            separator='\n',
            chunk_size=2000,
            chunk_overlap=200,
            length_function=len
        )
        chunks = text_splitter.split_text(text)
        print(f"Number of chunks: {len(chunks)}")

        embeddings = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))

        knowledge_base = FAISS.from_texts(chunks, embeddings)
        
        serialized_kb = pickle.dumps(knowledge_base)
        
        pdf_record = PDF(
            name=file.filename,
            size=file_size,
            content=serialized_kb
        )
        
        db.add(pdf_record)
        db.commit()
        db.refresh(pdf_record)
        
        return {
            "id": pdf_record.id,
            "msg": 'PDF uploaded and knowledge base created successfully'
        }

    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=500, detail=f'Server error: {str(error)}')

@app.post('/chat')
async def question_and_answer(question: Question, db: Session = Depends(get_db)):
    try:
        if not question.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")

        pdf_record = db.query(PDF).filter(PDF.id == question.pdf_id).first()
        if not pdf_record:
            raise HTTPException(status_code=404, detail='PDF not found')
        
        conversation = None
        if question.conversation_id:
            conversation = db.query(ChatHistory).filter(
                ChatHistory.id == question.conversation_id,
                ChatHistory.pdf_id == question.pdf_id
            ).first()
            if not conversation:
                raise HTTPException(status_code=404, detail='Conversation not found')
            print("Existing conversation:", conversation.conversation)
        else:
            conversation = ChatHistory(
                pdf_id=question.pdf_id,
                conversation=[]
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            print("New conversation created:", conversation.id)
        
        llm = OpenAI(model="gpt-3.5-turbo-instruct")
        
        prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template="""Use the following context to answer the question. If the answer is not in the context, say so.
                Context: {context}
                Question: {question}
                Answer:"""
                        )
        
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=False,
            chain_type_kwargs={"prompt": prompt_template}
        )
        
        with get_openai_callback() as cb:
            result = qa_chain.invoke({"query": question.question})
            response = result["result"]
            print(f"OpenAI API usage: {cb}")
        
        print("Before update:", conversation.conversation)
        conversation.conversation.append({
            "user": question.question,
            "ai": response,
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        print("After append:", conversation.conversation)
        flag_modified(conversation, "conversation")
        db.commit()
        print("After commit:", db.query(ChatHistory).filter(ChatHistory.id == conversation.id).first().conversation)
        
        return {
            "answer": response,
            "conversation_id": conversation.id
        }
        
    except SQLAlchemyError as db_error:
        db.rollback()
        print(f"Database error: {str(db_error)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")
    except Exception as error:
        db.rollback()
        print(f"Error in /chat endpoint: {str(error)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(error)}")

@app.get('/pdfs', response_model=List[PDFResponse])
def get_pdfs(db: Session = Depends(get_db)):
    try:
        pdfs = db.query(PDF).all()
        return [
            PDFResponse(
                id=pdf.id,
                name=pdf.name,
                size=bytes_to_kilobytes(pdf.size),
                uploaded_date=pdf.uploaded_date
            ) for pdf in pdfs
        ]
    except Exception as error:
        raise HTTPException(status_code=500, detail=f'Server error: {str(error)}')

@app.get('/conversations/{pdf_id}', response_model=List[ConversationResponse])
def get_conversations(pdf_id: str, db: Session = Depends(get_db)):
    try:
        conversations = db.query(ChatHistory).filter(ChatHistory.pdf_id == pdf_id).all()
        return [
            ConversationResponse(
                id=conv.id,
                pdf_id=conv.pdf_id,
                conversation=conv.conversation,
                created_at=conv.created_at
            ) for conv in conversations
        ]
    except Exception as error:
        raise HTTPException(status_code=500, detail=f'Server error: {str(error)}')

@app.delete('/pdfs/{pdf_id}')
def delete_pdf(pdf_id: str, db: Session = Depends(get_db)):
    try:
        pdf = db.query(PDF).filter(PDF.id == pdf_id).first()
        if not pdf:
            raise HTTPException(status_code=404, detail='PDF not found')
        
        db.delete(pdf)
        db.commit()
        
        return {"msg": "PDF and its conversations deleted successfully"}
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=500, detail=f'Server error: {str(error)}')


@app.get('/pdfs/{pdf_id}', response_model=PDFResponse)
def get_single_pdf(pdf_id: str, db: Session = Depends(get_db)):
    try:
        pdf = db.query(PDF).filter(PDF.id == pdf_id).first()
        if not pdf:
            raise HTTPException(status_code=404, detail='PDF not found')
        
        return PDFResponse(
            id=pdf.id,
            name=pdf.name,
            size=bytes_to_kilobytes(pdf.size),
            uploaded_date=pdf.uploaded_date
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail=f'Server error: {str(error)}')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
