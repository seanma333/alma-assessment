from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from typing import List
from pydantic import EmailStr
from os import getenv
from dotenv import load_dotenv

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

async def send_lead_notification(
    lead_email: EmailStr,
    lead_name: str,
    attorney_emails: List[EmailStr]
):
    # Email to prospect
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
    )

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
    )

    await fastmail.send_message(prospect_message)
    await fastmail.send_message(attorney_message)
