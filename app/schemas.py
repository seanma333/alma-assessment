from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from app.models import LeadStatus, UserRole, EmailStatus

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

class FailedEmailBase(BaseModel):
    lead_name: str
    lead_email: str
    attorney_emails: List[str]
    error_message: str

class FailedEmail(FailedEmailBase):
    id: int
    lead_id: int
    lead_uuid: UUID
    status: EmailStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class FailedEmailResend(BaseModel):
    failed_email_id: int

class TokenData(BaseModel):
    email: Optional[str] = None
