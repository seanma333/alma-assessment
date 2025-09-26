from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta
import io
import mimetypes
import json
import time
from collections import defaultdict

from app.database import get_db, engine
from app.models import Base, Lead, User, LeadStatus, FailedEmail, EmailStatus
from app.schemas import Lead as LeadSchema, User as UserSchema, Token, FailedEmail as FailedEmailSchema, LeadStatusUpdate
from app.auth import (
    get_current_user,
    get_current_admin_user,
    get_current_attorney_user,
    get_password_hash,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.email import send_lead_notification, send_lead_confirmation
from app.s3_service import s3_service
from dotenv import load_dotenv

load_dotenv()

# Database tables are now managed by Alembic migrations
# Run 'alembic upgrade head' to apply migrations

app = FastAPI(title="Leads Management API")

# Rate limiting for lead submissions
LEAD_SUBMISSION_RATE_LIMIT = 5  # Max 5 submissions per minute per IP
rate_limit_tracker = defaultdict(list)

def get_download_url(request: Request, lead_uuid: str) -> str:
    """Generate download URL for a lead's resume"""
    base_url = str(request.base_url).rstrip('/')
    return f"{base_url}/leads/{lead_uuid}/resume"

def check_rate_limit(client_ip: str) -> bool:
    """Check if client has exceeded rate limit"""
    current_time = time.time()
    minute_ago = current_time - 60

    # Clean old entries
    rate_limit_tracker[client_ip] = [
        timestamp for timestamp in rate_limit_tracker[client_ip]
        if timestamp > minute_ago
    ]

    # Check if limit exceeded
    if len(rate_limit_tracker[client_ip]) >= LEAD_SUBMISSION_RATE_LIMIT:
        return False

    # Add current request
    rate_limit_tracker[client_ip].append(current_time)
    return True

def validate_email_format(email: str) -> None:
    """Validate email format"""
    if not email or "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )

    parts = email.split("@")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )

    if "." not in parts[1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )

def check_email_exists(email: str, db: Session) -> None:
    """Check if email already exists in database"""
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )

# File validation constants
ALLOWED_FILE_TYPES = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'application/rtf'
}

ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt', '.rtf'}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

def validate_resume_file(file: UploadFile) -> None:
    """
    Validate resume file for type and size
    """
    # Check if file is provided
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )

    # Check file size
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size allowed is {MAX_FILE_SIZE // (1024*1024)}MB"
        )

    # Check file extension
    file_extension = '.' + file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Check MIME type if available (additional security check)
    if file.content_type and file.content_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: PDF, DOC, DOCX, TXT, RTF"
        )

    # Additional security: Check for suspicious file names
    suspicious_patterns = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
    if any(pattern in file.filename for pattern in suspicious_patterns):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file name. Please use a simple filename without special characters."
        )

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
    request: Request = None,
    db: Session = Depends(get_db)
):
    # Rate limiting check
    client_ip = request.client.host if request else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later."
        )

    # Validate email format
    validate_email_format(email)

    # Validate the resume file
    validate_resume_file(resume)

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

    # Send notification emails (separate lead and attorney emails)
    attorney_emails = [user.email for user in db.query(User).filter(User.role == "ATTORNEY").all()]

    # Send email to lead (confirmation)
    try:
        await send_lead_confirmation(
            lead_email=email,
            lead_name=f"{first_name} {last_name}"
        )
    except Exception as e:
        # Log lead email failure but don't track in failed_emails (not critical)
        print(f"Lead confirmation email failed: {e}")

    # Send notification emails to attorneys (critical - track failures)
    if attorney_emails:  # Only send if there are attorneys
        try:
            await send_lead_notification(
                lead_email=email,
                lead_name=f"{first_name} {last_name}",
                attorney_emails=attorney_emails
            )
        except Exception as e:
            # Log the error and track it in failed_emails table
            print(f"Attorney notification email failed: {e}")

            # Create failed email record
            failed_email = FailedEmail(
                lead_id=db_lead.id,
                lead_uuid=db_lead.uuid,
                lead_name=f"{first_name} {last_name}",
                lead_email=email,
                attorney_emails=json.dumps(attorney_emails),
                error_message=str(e),
                status=EmailStatus.FAILED
            )
            db.add(failed_email)
            db.commit()

    # Add download URL to the response
    lead_data = {
        "uuid": db_lead.uuid,
        "first_name": db_lead.first_name,
        "last_name": db_lead.last_name,
        "email": db_lead.email,
        "resume_download_url": get_download_url(request, str(db_lead.uuid)),
        "status": db_lead.status,
        "created_at": db_lead.created_at,
        "updated_at": db_lead.updated_at
    }
    return lead_data

@app.get("/leads/", response_model=List[LeadSchema])
async def get_leads(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_attorney_user)
):
    leads = db.query(Lead).all()

    # Add download URLs to each lead
    leads_with_download_urls = []
    for lead in leads:
        lead_data = {
            "uuid": lead.uuid,
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "email": lead.email,
            "resume_download_url": get_download_url(request, str(lead.uuid)),
            "status": lead.status,
            "created_at": lead.created_at,
            "updated_at": lead.updated_at
        }
        leads_with_download_urls.append(lead_data)

    return leads_with_download_urls

@app.get("/leads/{lead_uuid}", response_model=LeadSchema)
async def get_lead(
    lead_uuid: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_attorney_user)
):
    """Get a single lead by UUID"""
    lead = db.query(Lead).filter(Lead.uuid == lead_uuid).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Add download URL to the response
    lead_data = {
        "uuid": lead.uuid,
        "first_name": lead.first_name,
        "last_name": lead.last_name,
        "email": lead.email,
        "resume_download_url": get_download_url(request, str(lead.uuid)),
        "status": lead.status,
        "created_at": lead.created_at,
        "updated_at": lead.updated_at
    }
    return lead_data

@app.put("/leads/{lead_uuid}/status", response_model=LeadSchema)
async def update_lead_status(
    lead_uuid: str,
    status_update: LeadStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_attorney_user)
):
    lead = db.query(Lead).filter(Lead.uuid == lead_uuid).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.status = status_update.status
    db.commit()
    db.refresh(lead)

    # Add download URL to the response
    lead_data = {
        "uuid": lead.uuid,
        "first_name": lead.first_name,
        "last_name": lead.last_name,
        "email": lead.email,
        "resume_download_url": get_download_url(request, str(lead.uuid)),
        "status": lead.status,
        "created_at": lead.created_at,
        "updated_at": lead.updated_at
    }
    return lead_data

@app.post("/users/", response_model=UserSchema)
async def create_user(
    email: str,
    password: str,
    role: str = "ATTORNEY",  # Default to attorney role
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)  # Only admins can create users
):
    # Validate email format
    validate_email_format(email)

    # Check if email already exists
    check_email_exists(email, db)

    # Validate role
    if role not in ["ATTORNEY", "ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'ATTORNEY' or 'ADMIN'"
        )

    db_user = User(
        email=email,
        hashed_password=get_password_hash(password),
        role=role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/leads/{lead_uuid}/resume")
async def download_resume(
    lead_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_attorney_user)
):
    """
    Download resume for a specific lead. Requires authentication.
    """
    # Get the lead from database
    lead = db.query(Lead).filter(Lead.uuid == lead_uuid).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    try:
        # Download file from S3
        file_content, content_type = s3_service.download_file(lead.resume_path)

        # Create a filename for download
        filename = f"resume_{lead.first_name}_{lead.last_name}.pdf"

        # Return the file as a streaming response
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download resume: {str(e)}"
        )

# Admin APIs for failed email management
@app.get("/admin/failed-emails/", response_model=List[FailedEmailSchema])
async def get_failed_emails(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Get all failed email notifications (Admin only)"""
    failed_emails = db.query(FailedEmail).filter(FailedEmail.status == EmailStatus.FAILED).all()
    return failed_emails

@app.post("/admin/failed-emails/{failed_email_id}/resend")
async def resend_failed_email(
    failed_email_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Resend a failed email notification (Admin only)"""
    failed_email = db.query(FailedEmail).filter(FailedEmail.id == failed_email_id).first()
    if not failed_email:
        raise HTTPException(status_code=404, detail="Failed email record not found")

    if failed_email.status != EmailStatus.FAILED:
        raise HTTPException(status_code=400, detail="Email is not in failed status")

    try:
        # Parse attorney emails from JSON
        attorney_emails = json.loads(failed_email.attorney_emails)

        # Attempt to resend the email
        await send_lead_notification(
            lead_email=failed_email.lead_email,
            lead_name=failed_email.lead_name,
            attorney_emails=attorney_emails
        )

        # Update status to SENT and remove from failed_emails table
        db.delete(failed_email)
        db.commit()

        return {"message": "Email sent successfully and removed from failed emails"}

    except Exception as e:
        # Update error message if resend fails
        failed_email.error_message = f"Resend failed: {str(e)}"
        db.commit()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to resend email: {str(e)}"
        )

@app.delete("/admin/failed-emails/{failed_email_id}")
async def delete_failed_email(
    failed_email_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a failed email record (Admin only)"""
    failed_email = db.query(FailedEmail).filter(FailedEmail.id == failed_email_id).first()
    if not failed_email:
        raise HTTPException(status_code=404, detail="Failed email record not found")

    db.delete(failed_email)
    db.commit()

    return {"message": "Failed email record deleted successfully"}

@app.post("/users/initial", response_model=UserSchema)
async def create_initial_user(
    email: str,
    password: str,
    db: Session = Depends(get_db)
):
    # Validate email format
    validate_email_format(email)

    # Check if email already exists
    check_email_exists(email, db)

    # Check if any users already exist
    existing_user = db.query(User).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Initial user already exists. Use /users/ endpoint with authentication."
        )

    # Create the first user as an admin
    db_user = User(
        email=email,
        hashed_password=get_password_hash(password),
        role="ADMIN"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
