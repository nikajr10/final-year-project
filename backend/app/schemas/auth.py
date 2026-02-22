from pydantic import BaseModel, EmailStr

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# --- NEW: Schema for the Signup Payload ---
class UserCreate(BaseModel):
    name: str       
    email: EmailStr 
    password: str