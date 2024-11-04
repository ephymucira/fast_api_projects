import logging
from fastapi import FastAPI, Request, HTTPException, status,Depends
from tortoise.contrib.fastapi import register_tortoise
from tortoise.signals import post_save
from typing import List, Optional, Type
from tortoise import BaseDBAsyncClient
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from models import *
from authentications import *
from emailss import *
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

#image upload
from fastapi import File, UploadFile
import secrets
from fastapi.staticfiles import StaticFiles
from PIL import Image


# Initialize logging at the very top of the file
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

 

oath2_scheme = OAuth2PasswordBearer(tokenUrl='token')

#static file setup config

app.mount("/static", StaticFiles(directory="static"),name = "static")


@app.post("/token")
async def generate_token(request_form:OAuth2PasswordRequestForm = Depends()):
    token = await token_generator(request_form.username, request_form.password)
    return {"access_token":token, "token_type":"bearer"}

async def get_current_user(token: str = Depends(oath2_scheme)):
    try :
        payload = jwt.decode(token,config_credentials["SECRET"],algorithms=["HS256"])
        user = await User.get(id = payload.get("id"))

    except:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail= "Invalid username or password",
            headers={"WWW-Authenticate":"Bearer"}
        )
    return await user

@app.post("/user/me")
async def user_login(user: user_pydanticIn = Depends(get_current_user)):
    #return business details of the user
    business =  await Business.get(owner=user)
    logo = business.logo
    logo_path = "localhost:8000/static/images"+logo




    return {
        "status":"ok",
        "data":{
            "username": user.username,
            "email":user.email,
            "verified":user.is_verified,
            "joined_date":user.join_date.strftime("%b %d %Y"),
            "logo":logo_path

        }
    }



register_tortoise(
    app,
    db_url="sqlite://database.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True
)

@app.post("/register")
async def user_registration(user: user_pydanticIn):
    try:
        logger.info(f"Received registration request with username: {user.username} and email: {user.email}")
        
        # Database connection check
        try:
            await User.first()
        except Exception as db_error:
            logger.error(f"Database connection error: {db_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database connection error"
            )

        # Email check
        existing_user = await User.get_or_none(email=user.email)
        if existing_user:
            logger.warning(f"Attempted registration with existing email: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email {user.email} is already registered"
            )

        # Username check
        existing_username = await User.get_or_none(username=user.username)
        if existing_username:
            logger.warning(f"Attempted registration with existing username: {user.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username {user.username} is already taken"
            )

        # Create user
        try:
            user_info = user.dict(exclude_unset=True)
            user_info["password"] = get_hashed_password(user_info["password"])
            # Add a flag to prevent duplicate email sending
            user_info["email_sent"] = False
            user_obj = await User.create(**user_info)
            logger.info(f"Successfully created user: {user_obj.username}")
        except Exception as create_error:
            logger.error(f"Error creating user: {create_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating user account"
            )

        # Send verification email
        try:
            await send_email([user_obj.email], user_obj)
            user_obj.email_sent = True
            await user_obj.save()
            logger.info(f"Verification email sent to: {user_obj.email}")
        except Exception as email_error:
            logger.error(f"Error sending verification email: {email_error}")
            
        return {
            "status": "success",
            "data": f"Hello {user_obj.username}, thanks for choosing our services. Please check your email to confirm registration."
        }

    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during registration"
        )

@post_save(User)
async def create_business(
    sender: "Type[User]",
    instance: User,
    created: bool,
    using_db: "Optional[BaseDBAsyncClient]",
    update_fields: List[str]
) -> None:
    try:
        if created:
            # Create business
            business_obj = await Business.create(
                business_name=instance.username,
                owner=instance
            )
            await business_pydantic.from_tortoise_orm(business_obj)
            
            # Only send email if it hasn't been sent already
            if not getattr(instance, 'email_sent', False):
                await send_email([instance.email], instance)
                instance.email_sent = True
                await instance.save()
    except Exception as e:
        logger.error(f"Error in post_save signal handler: {e}")

@app.get("/")
def index():
    return {"message": "Hello World"}

templates = Jinja2Templates(directory="templates")

@app.get("/verification", response_class=HTMLResponse)
async def email_verification(request: Request, token: str):
    try:
        user = await verify_token(token)
        if user and not user.is_verified:
            user.is_verified = True
            await user.save()
            return templates.TemplateResponse(
                "verification.html",
                {"request": request, "username": user.username}
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"Error during verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error during verification"
        )
# for debugging purposes
@app.get("/check_user")
async def check_user(email: str):
    try:
        user = await User.get_or_none(email=email)
        return {"exists": user is not None,"password":user.password}
    except Exception as e:
        logger.error(f"Error checking user existence: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error checking user existence"
        )


@app.post("/uploadfile/profile")
async def create_upload_file(file:UploadFile = File(...), user: user_pydantic = Depends(get_current_user)):

    FILEPATH = "./static/images/"
    filename = file.filename
    #test.png == ["test","png"]
    extension = filename.split(".")[1]

    if extension not in ["png","jpg"]:
        return {"status":"error","detail":"File extension not allowed"}

    token_name = secrets.token_hex(10) + "." + extension
    generated_name = FILEPATH + token_name
    file_content = await file.read()

    with open(generated_name,"wb") as file:
        file.write(file_content)

    
    #pillow

    img = Image.open(generated_name)
    img  = img.resize(size = (200,200))
    img.save(generated_name)


    file.close()

    business = await Business.get(owner = user)
    owner = await business.owner

    if owner == user:
        business.logo = token_name
        await business.save()

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this action",
            headers = {"WWW-Authenticate":"Bearer"}
        )

    file_url = "localhost:8000"+ generated_name[1:]

    return {
        "status":"ok",
        "filename":file_url
    }


@app.post("/uploadfile/product/{id}")
async def create_upload_file(id:int, file:UploadFile = File(...),user:user_pydantic = Depends(get_current_user) ):
    FILEPATH = "./static/images/"
    filename = file.filename
    #test.png == ["test","png"]
    extension = filename.split(".")[1]

    if extension not in ["png","jpg"]:
        return {"status":"error","detail":"File extension not allowed"}

    token_name = secrets.token_hex(10) + "." + extension
    generated_name = FILEPATH + token_name
    file_content = await file.read()

    with open(generated_name,"wb") as file:
        file.write(file_content)

    
    #pillow

    img = Image.open(generated_name)
    img  = img.resize(size = (200,200))
    img.save(generated_name)


    file.close()

    product = await Product.get(id=id)
    business = await product.business
    owner = await business.owner

    if owner == user:
        product.product_image = token_name
        await product.save()

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this action",
            headers = {"WWW-Authenticate":"Bearer"}
        )
    
    file_url = "localhost:8000"+ generated_name[1:]

    return {
        "status":"ok",
        "filename":file_url
    }


#crud functionalities

@app.post("/products")
async def add_new_product(product:product_pydanticIn ,user: user_pydantic = Depends(get_current_user)):

    product = product.dict(exclude_unset=True)

    #to avoid division by zero error

    if product["original_price"] > 0:
        product["percentage_discount"] = ((product["original_price"]-product["new_price"])/ product["original_price"]) * 100

        product_obj = await Product.create(**product, business = user)

        product_obj = await product_pydantic.from_tortoise_orm(product_obj)

        
