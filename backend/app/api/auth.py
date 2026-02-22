from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import User
from app.schemas.auth import UserLogin, Token
from app.core.security import verify_password, create_access_token
from datetime import timedelta

router = APIRouter()
ACCESS_TOKEN_EXPIRE_MINUTES = 60

@router.post("/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    # 1. Find user by email
    user = db.query(User).filter(User.email == user_credentials.email).first()
    
    # 2. Verify user exists and password is correct
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Generate JWT Token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}