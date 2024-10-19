from typing import List

from fastapi import BackgroundTasks, UploadFile,File,Form,Depends, HTTPException,status
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import BaseModel, EmailStr
from starlette.responses import JSONResponse
from dotenv import dotenv_values
from models import User
import jwt
cofig_details = dotenv_values(".env")


conf = ConnectionConfig(
    MAIL_USERNAME = cofig_details["EMAIL"],
    MAIL_PASSWORD = cofig_details["PASS"],
    MAIL_FROM = cofig_details["EMAIL"],
    MAIL_PORT = 587,
    MAIL_SERVER = "smtp.gmail.com",
    MAIL_STARTTLS = True,  # Correct field
    MAIL_SSL_TLS = False,  # Correct field
    USE_CREDENTIALS = True
)

class EmailSchema(BaseModel):
    email:List[EmailStr]

async def send_email(email: List, instance:User):
    token_data = {
        "id":instance.id,
        "username": instance.username

    }

    token = jwt.encode(token_data,cofig_details["SECRET"],algorithm="HS256")

    template = f"""
          <!DOCTYPE html>
          <html>
              <head>

              </head>

              <body>
                  <div style="display: flex; align-items:center; justify-content:center; flex-direction:column;">

                       <h3> Account Verification</h3><br>

                       <p>
                            Thanks for choosing EasyShopas, please click on the button below to verify your account.
                       </p>

                       <a style="margin-top:1rem; padding:1rem;border-radius:0.5rem;font-size:1rem;text-decoration:none;background:#0275d8;color:white;" href="http://localhost:8000/verification/?token={token}"> Verify your email</a>

                       <p> Please ignore this email if you did not create an account with us.Thanks</p>
                  </div>

              </body>

           </html>

    """ 

    message = MessageSchema(
        subject="EasyShopas Account Verification Email",
        recipients = email,
        body = template,
        subtype = "html"
    )     

    fm = FastMail(conf)

    await fm.send_message(message=message)

