import pickle
import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.exc import SQLAlchemyError
from langchain_community.llms.openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_community.callbacks.manager import get_openai_callback

from app.db import get_db
from app.models.chat_history_model import ChatHistory
from app.models.user_model import User
from app.models.pdf_model import PDF
from app.types.chat_type import Question, ConversationResponse
from app.services.auth_service import get_current_user, verify_user_owns_pdf

router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)

@router.post('/')
async def question_and_answer(
    question: Question,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        if not question.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")

        pdf_record = verify_user_owns_pdf(question.pdf_id, current_user, db)
        
        # Load the knowledge base from the PDF record
        knowledge_base = pickle.loads(pdf_record.content)
        
        # Check if the conversation already exists
        conversation = db.query(ChatHistory).filter(
            ChatHistory.pdf_id == question.pdf_id
        ).first()
        
        # If no conversation exists, create a new one
        if not conversation:
            conversation = ChatHistory(
                pdf_id=question.pdf_id,
                conversation=[]
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            print("New conversation created:", conversation.id)
        else:
            pdf = db.query(PDF).filter(PDF.id == conversation.pdf_id).first()
            if pdf.user_id != current_user.id:
                raise HTTPException(status_code=403, detail='Not authorized to access this conversation')
            print("Existing conversation:", conversation.conversation)
        
        llm = OpenAI(model="gpt-3.5-turbo-instruct")
        
        # Define the prompt template
        prompt_template = PromptTemplate(
                input_variables=["context", "question"],
                template="""You are an intelligent assistant helping a user understand information from their PDF document.

            Instructions:
            - Carefully analyze the provided context from the PDF document.
            - Answer the user's question based ONLY on the information provided in the context.
            - If the answer is fully contained in the context, provide a clear, concise response.
            - If the answer is partially in the context, provide what you can find and indicate what information is missing.
            - If the answer is not in the context at all, politely state that the information isn't present in the provided sections.
            - Do not make up information or use knowledge outside of the provided context.
            - If the context is ambiguous or unclear, acknowledge this and explain what's confusing.
            - For complex questions, break down your answer into structured parts.
            - When referencing specific parts of the document, indicate where the information came from (e.g., "According to page 5..." or "In the section about...").
            - If the user asks for a summary, focus on key points rather than every detail.

            Context from PDF: {context}

            User Question: {question}

            Answer:"""
            )
                    
                    # Create the retriever with a search method
        retriever = knowledge_base.as_retriever(search_kwargs={"k": 4})
        
        # Create the QA chain with the LLM and retriever
        # Use the "stuff" chain type for simplicity
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=False,
            chain_type_kwargs={"prompt": prompt_template}
        )
        
        # This is for debugging purposes, to see total tokens used and cost
        with get_openai_callback() as cb:
            result = qa_chain.invoke({"query": question.question})
            response = result["result"]
            print(f"OpenAI API usage: {cb}")
        
        # Append the new question and answer to the conversation
        conversation.conversation.append({
            "user": question.question,
            "ai": response,
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        # Update the conversation in the database
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
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        db.rollback()
        print(f"Error in /chat endpoint: {str(error)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(error)}")

@router.get('/conversations/{pdf_id}', response_model=List[ConversationResponse])
def get_conversations(
    pdf_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        verify_user_owns_pdf(pdf_id, current_user, db)
        
        conversations = db.query(ChatHistory).filter(ChatHistory.pdf_id == pdf_id).all()
        return [
            ConversationResponse(
                id=conv.id,
                pdf_id=conv.pdf_id,
                conversation=conv.conversation,
                created_at=conv.created_at
            ) for conv in conversations
        ]
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f'Server error: {str(error)}')