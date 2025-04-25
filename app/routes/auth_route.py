from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user_model import User
from app.types.auth_type import UserCreate, UserLogin, User as UserSchema
from app.services.auth_service import (
    authenticate_user, create_user, get_current_user, 
    create_access_token, ACCESS_TOKEN_EXPIRE_DAYS
)

router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)

@router.post("/register", response_model=dict)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    print("Registering user:", user.email)
    return create_user(db=db, user=user)

@router.post("/login", response_model=dict)
def login(
    user_data: UserLogin,
    response: Response,
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password, please provide valid credentials",
        )
    
    token_data = {
        "id": user.id,
        "email": user.email
    }
    token = create_access_token(token_data)
    
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # in seconds
        samesite="lax",
        secure=False 
    )
    
    return {
        "message": "Login successful",
        "user_id": user.id,
        "email": user.email
    }

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("auth_token")
    
    return {"message": "Logout successful"}

@router.get("/me", response_model=UserSchema)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user