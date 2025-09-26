from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from uuid import UUID
from app.models import LeadStatus, UserRole

class LeadBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr

class Lead(LeadBase):
    uuid: UUID
    resume_download_url: str  # Public download URL
    status: LeadStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    email: EmailStr

class User(UserBase):
    id: int
    role: UserRole
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
