from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from typing import List
from pydantic import EmailStr
from os import getenv
from dotenv import load_dotenv
import asyncio
import random
from functools import wraps

load_dotenv()

conf = ConnectionConfig(
    MAIL_USERNAME=getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=getenv("MAIL_PASSWORD"),
    MAIL_FROM=getenv("MAIL_FROM"),
    MAIL_PORT=int(getenv("MAIL_PORT", "587")),
    MAIL_SERVER=getenv("MAIL_SERVER"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)

fastmail = FastMail(conf)

# Retry configuration
MAX_RETRIES = 3
BASE_DELAY = 1  # Base delay in seconds
MAX_DELAY = 60  # Maximum delay in seconds

def exponential_backoff_retry(max_retries: int = MAX_RETRIES, base_delay: float = BASE_DELAY, max_delay: float = MAX_DELAY):
    """Decorator for exponential backoff retry logic"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # Don't retry on the last attempt
                    if attempt == max_retries:
                        break

                    # Calculate delay with exponential backoff and jitter
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0.1, 0.3) * delay
                    total_delay = delay + jitter

                    print(f"Email attempt {attempt + 1} failed: {str(e)}. Retrying in {total_delay:.2f} seconds...")
                    await asyncio.sleep(total_delay)

            # If all retries failed, raise the last exception
            raise last_exception

        return wrapper
    return decorator

async def send_email_with_retry(message: MessageSchema) -> None:
    """Send email with exponential backoff retry logic"""
    @exponential_backoff_retry()
    async def _send_email():
        await fastmail.send_message(message)

    await _send_email()

async def send_lead_notification(
    lead_email: EmailStr,
    lead_name: str,
    attorney_emails: List[EmailStr]
):
    """Send notification email to attorneys only"""
    # Email to attorneys
    attorney_message = MessageSchema(
        subject="New Lead Submission",
        recipients=attorney_emails,
        body=f"""
        A new lead has been submitted:

        Name: {lead_name}
        Email: {lead_email}

        Please review the submission in the leads management system.
        """,
        subtype=MessageType.plain
    )

    await send_email_with_retry(attorney_message)

async def send_lead_confirmation(
    lead_email: EmailStr,
    lead_name: str
):
    """Send confirmation email to lead only"""
    prospect_message = MessageSchema(
        subject="Thank you for your application",
        recipients=[lead_email],
        body=f"""
        Dear {lead_name},

        Thank you for submitting your application. Our team will review your information
        and get back to you shortly.

        Best regards,
        The Team
        """,
        subtype=MessageType.plain
    )

    await send_email_with_retry(prospect_message)
