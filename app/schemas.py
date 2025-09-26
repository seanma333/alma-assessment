from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from app.models import LeadStatus

class LeadBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr

class LeadCreate(LeadBase):
    pass

class Lead(LeadBase):
    id: int
    resume_path: str
    status: LeadStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
