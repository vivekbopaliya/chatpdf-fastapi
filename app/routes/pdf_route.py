import io
import pickle
from typing import List
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from pypdf import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from app.db import get_db
from app.models.pdf_model import PDF
from app.models.user_model import User
from app.types.pdf_type import PDFResponse
from app.services.auth_service import get_current_user, verify_user_owns_pdf

router = APIRouter(
    prefix="/pdf",
    tags=["pdf"]
)

def bytes_to_kilobytes(bytes_value):
    return f"{bytes_value / 1024:.2f} KB"

@router.post('/upload', response_model=dict)
async def pdf_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file:
        raise HTTPException(status_code=400, detail='Please upload a file')
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail='Uploaded file must be a PDF')
    
    try:
        # Read the PDF file binary data
        pdf_binary_data = await file.read()
        
        file_size = len(pdf_binary_data)
        
        pdf = io.BytesIO(pdf_binary_data)
        # Use PyPDF2 to read the PDF content
        pdf_content = PdfReader(pdf)

        text = ''
        for i in pdf_content.pages:
            text += i.extract_text()



        # Split the text into chunks
        text_splitter = CharacterTextSplitter(
            separator='\n',
            chunk_size=2000,
            chunk_overlap=200,
            length_function=len
        )
        chunks = text_splitter.split_text(text)
        print(f"Number of chunks: {len(chunks)}")

        # Create embeddings and knowledge base
        embeddings = OpenAIEmbeddings()

#        # Create a FAISS knowledge base from the chunks
        knowledge_base = FAISS.from_texts(chunks, embeddings)
        
        # Save the knowledge base to a file or database
        serialized_kb = pickle.dumps(knowledge_base)
        
        print("serialized_kb:", serialized_kb[:100])
        # Store the PDF and knowledge base in the database  
        pdf_record = PDF(
            name=file.filename,
            size=file_size,
            content=serialized_kb,
            user_id=current_user.id 
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

@router.get('/pdfs', response_model=List[PDFResponse])
def get_pdfs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        pdfs = db.query(PDF).filter(PDF.user_id == current_user.id).all()
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

@router.get('/{pdf_id}', response_model=PDFResponse)
def get_single_pdf(
    pdf_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        pdf = verify_user_owns_pdf(pdf_id, current_user, db)
        
        return PDFResponse(
            id=pdf.id,
            name=pdf.name,
            size=bytes_to_kilobytes(pdf.size),
            uploaded_date=pdf.uploaded_date
        )
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f'Server error: {str(error)}')

@router.delete('/{pdf_id}')
def delete_pdf(
    pdf_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        pdf = verify_user_owns_pdf(pdf_id, current_user, db)
        
        db.delete(pdf)
        db.commit()
        
        return {"msg": "PDF and associated conversations deleted successfully"}
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=500, detail=f'Server error: {str(error)}')