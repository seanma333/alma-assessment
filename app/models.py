from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
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

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole, name="user_role"), default=UserRole.ATTORNEY, nullable=False)
    is_active = Column(SQLEnum(UserStatus, name="user_status"), default=UserStatus.TRUE, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
