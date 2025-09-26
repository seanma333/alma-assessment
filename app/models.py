from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()

class LeadStatus(str, Enum):
    PENDING = "PENDING"
    REACHED_OUT = "REACHED_OUT"

class UserStatus(str, Enum):
    TRUE = "true"
    FALSE = "false"

class UserRole(str, Enum):
    ATTORNEY = "ATTORNEY"
    ADMIN = "ADMIN"

class EmailStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    resume_path = Column(String, nullable=False)
    status = Column(SQLEnum(LeadStatus, name="lead_status"), default=LeadStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to failed emails
    failed_emails = relationship("FailedEmail", back_populates="lead")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole, name="user_role"), default=UserRole.ATTORNEY, nullable=False)
    is_active = Column(SQLEnum(UserStatus, name="user_status"), default=UserStatus.TRUE, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FailedEmail(Base):
    __tablename__ = "failed_emails"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    lead_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)
    lead_name = Column(String, nullable=False)  # Lead's full name
    lead_email = Column(String, nullable=False)  # Lead's email
    attorney_emails = Column(Text, nullable=False)  # JSON string of attorney emails
    error_message = Column(Text, nullable=False)  # Error details
    status = Column(SQLEnum(EmailStatus, name="email_status"), default=EmailStatus.FAILED, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to lead
    lead = relationship("Lead", back_populates="failed_emails")

# Add relationship to Lead model
# This will be added to the Lead model
