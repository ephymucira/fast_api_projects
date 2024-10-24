from passlib.context import CryptContext
import jwt
from dotenv import dotenv_values
from models import User
from fastapi import status
from fastapi.exceptions import HTTPException



config_credentials = dotenv_values(".env")

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

def get_hashed_password(password):
    try:
        return pwd_context.hash(password)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error hashing password: {str(e)}"
        )



async def verify_token(token:str):

    try:
        payload = jwt.decode(token,config_credentials["SECRET"],algorithm=["HS256"])
        user = await User.get(id = payload.get("id"))
    
    except:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate":"Bearer"}
        )
    return user 
