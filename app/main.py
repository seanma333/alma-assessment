from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta

from app.database import get_db, engine
from app.models import Base, Lead, User, LeadStatus
from app.schemas import LeadCreate, Lead as LeadSchema, User as UserSchema, Token
from app.auth import (
    get_current_user,
    get_password_hash,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.email import send_lead_notification
from app.s3_service import s3_service
from dotenv import load_dotenv

load_dotenv()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Leads Management API")

@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/leads/", response_model=LeadSchema)
async def create_lead(
    first_name: str,
    last_name: str,
    email: str,
    resume: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Upload the resume file to S3
    s3_url = await s3_service.upload_file(resume)

    # Create lead in database
    db_lead = Lead(
        first_name=first_name,
        last_name=last_name,
        email=email,
        resume_path=s3_url
    )
    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)

    # Send notification emails
    attorney_emails = [user.email for user in db.query(User).all()]
    await send_lead_notification(
        lead_email=email,
        lead_name=f"{first_name} {last_name}",
        attorney_emails=attorney_emails
    )

    return db_lead

@app.get("/leads/", response_model=List[LeadSchema])
async def get_leads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    leads = db.query(Lead).all()
    return leads

@app.put("/leads/{lead_id}/status", response_model=LeadSchema)
async def update_lead_status(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.status = LeadStatus.REACHED_OUT
    db.commit()
    db.refresh(lead)
    return lead

@app.post("/users/", response_model=UserSchema)
async def create_user(
    email: str,
    password: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Only existing users can create new users
):
    db_user = User(
        email=email,
        hashed_password=get_password_hash(password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
