from typing import List
from fastapi import BackgroundTasks, HTTPException, status
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from pydantic import BaseModel, EmailStr
from dotenv import dotenv_values
from models import User
import jwt
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
config_details = dotenv_values(".env")

# Validate required environment variables
required_configs = ["EMAIL", "PASS", "SECRET"]
for config in required_configs:
    if config not in config_details:
        raise ValueError(f"Missing required environment variable: {config}")

# Email configuration
conf = ConnectionConfig(
    MAIL_USERNAME=config_details["EMAIL"],
    MAIL_PASSWORD=config_details["PASS"],
    MAIL_FROM=config_details["EMAIL"],
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

class EmailSchema(BaseModel):
    email: List[EmailStr]

def get_verification_template(username: str, verification_url: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f9f9f9;
                border-radius: 5px;
            }}
            .button {{
                display: inline-block;
                padding: 10px 20px;
                background-color: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h3>Account Verification</h3>
            <p>Hello {username},</p>
            <p>Thanks for choosing EasyShopas. Please click on the link below to verify your account:</p>
            <a href="{verification_url}" class="button">Verify your email</a>
            <p>Or copy and paste this link in your browser:</p>
            <p>{verification_url}</p>
            <p>This link will expire in 24 hours.</p>
            <p>Please ignore this email if you did not create an account with us.</p>
        </div>
    </body>
    </html>
    """

async def send_email(email_list: List, instance: User):
    try:
        logger.info(f"Preparing to send email to: {email_list}")
        
        # Generate token
        token_data = {
            "id": str(instance.id),  # Convert UUID to string if needed
            "username": instance.username
        }
        
        logger.debug("Generating verification token")
        token = jwt.encode(token_data, config_details["SECRET"], algorithm="HS256")
        
        # Create verification URL
        verification_url = f"http://localhost:8000/verification/?token={token}"
        
        # Get email template
        template = get_verification_template(instance.username, verification_url)
        
        # Create message
        message = MessageSchema(
            subject="EasyShopas Account Verification Email",
            recipients=email_list,
            body=template,
            subtype="html"
        )

        # Initialize FastMail
        logger.debug("Initializing FastMail")
        fm = FastMail(conf)
        
        # Send email
        logger.info("Attempting to send email")
        await fm.send_message(message=message)
        logger.info(f"Email successfully sent to {email_list}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        # Log configuration details (excluding sensitive information)
        logger.debug(f"Mail server: {conf.MAIL_SERVER}")
        logger.debug(f"Mail port: {conf.MAIL_PORT}")
        logger.debug(f"From address: {conf.MAIL_FROM}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
        )
