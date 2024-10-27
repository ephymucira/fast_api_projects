from passlib.context import CryptContext
import jwt
from dotenv import dotenv_values
from models import User
from fastapi import status
from fastapi.exceptions import HTTPException

# from jose import (JWTError, jwt)
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)



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
        payload = jwt.decode(token,config_credentials["SECRET"],algorithms=["HS256"])
        user = await User.get(id = payload.get("id"))
    
    except:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate":"Bearer"}
        )
    return user 


# this code was just for debugging purposes
# async def verify_token(token: str):
#     try:
#         # Log the token for debugging
#         logger.debug(f"Attempting to verify token: {token}")
        
#         # Decode token
#         payload = jwt.decode(
#             token, 
#             config_credentials["SECRET"], 
#             algorithms=["HS256"]
#         )
#         logger.debug(f"Decoded payload: {payload}")
        
#         # Extract user ID
#         user_id = payload.get("id")
#         logger.debug(f"Extracted user ID: {user_id}")
        
#         if not user_id:
#             logger.error("No user ID found in token payload")
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Token missing user ID",
#                 headers={"WWW-Authenticate": "Bearer"}
#             )
        
#         # Try to get user from database
#         user = await User.get(id=user_id)
#         logger.debug(f"Retrieved user: {user}")
        
#         if not user:
#             logger.error(f"No user found for ID: {user_id}")
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="User not found",
#                 headers={"WWW-Authenticate": "Bearer"}
#             )
            
#         return user
        
#     except JWTError as e:
#         logger.error(f"JWT decode error: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid token format",
#             headers={"WWW-Authenticate": "Bearer"}
#         )
#     except Exception as e:
#         logger.error(f"Database or other error: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail=f"Verification error: {str(e)}",
#             headers={"WWW-Authenticate": "Bearer"}
#         )



async def verify_password(plain_password,hashed_password):
    return pwd_context.verify(plain_password,hashed_password)


async def authenticate_user(username,password):
    user = await User.get(username = username)

    if user and verify_password(password,user.password):
        return user
    return False

async def token_generator(username:str,password:str):
    user = await  authenticate_user(username,password)

    if not user:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail= "Invalid username or password",
            headers={"WWW-Authenticate":"Bearer"}
        )

    token_data = {
        "id":user.id,
        "username":user.username
    }

    token = jwt.encode(token_data, config_credentials['SECRET'],algorithms=["HS256"])

    return token
