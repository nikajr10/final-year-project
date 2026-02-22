from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import User
from app.schemas.auth import UserLogin, Token, UserCreate # <-- Import UserCreate
from app.core.security import verify_password, create_access_token, get_password_hash # <-- Import get_password_hash
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

# --- NEW: SIGNUP ENDPOINT ---
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # 1. Check if the email already exists in the database
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )
        
    # 2. Hash the password securely
    hashed_password = get_password_hash(user_in.password)
    
    # 3. Create the new user object (Mapping frontend 'name' to backend 'username')
    new_user = User(
        username=user_in.name,
        email=user_in.email,
        hashed_password=hashed_password,
        role="user" # Default role for new signups
    )
    
    # 4. Save to database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "status": "success", 
        "message": "User created successfully", 
        "user_email": new_user.email
    }