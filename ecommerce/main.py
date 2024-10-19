from fastapi import FastAPI,Request,HTTPException,status
from tortoise.contrib.fastapi import register_tortoise
from models import *
from authentications import *
from emailss import*


#signals
from tortoise.signals import post_save
from typing import List, Optional,Type
from tortoise import BaseDBAsyncClient

#response classes

from fastapi.responses import HTMLResponse

#templates
from fastapi.templating import Jinja2Templates


app = FastAPI()


register_tortoise(

    app,
    db_url = "sqlite://database.sqlite3",
    modules = {"models":["models"]},
    generate_schemas = True,
    add_exception_handlers = True

)


@post_save(User)
async def create_business(
    sender:"Type[User]",
    instance:User,
    created:bool,
    using_db:"Optional[BaseDBAsyncClient]",
    update_fields: List[str]

) -> None:
     if created:
        business_obj = await Business.create(
            business_name = instance.username, owner = instance
        )

        await business_pydantic.from_tortoise_orm(business_obj)

        #sending the email
        await send_email([instance.email], instance)



@app.get("/")
def index():
    return {"message":"Hello World"}

templates = Jinja2Templates(directory="templates")
@app.get("/verification",response_class=HTMLResponse)
async def email_verification(request:Request,token:str):
    user = await verify_token(token)

    if user and not user.is_verified:
        user.is_verified = True
        await user.save()
        return templates.TemplateResponse("verification.html",
                                           {"request":request,"username":user.username})

    raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate":"Bearer"}
        )

@app.post("/register")
async def user_registration(user:user_pydanticIn):
    user_info = user.dict(exclude_unset = True)
    user_info["password"] = get_hashed_password(user_info["password"])
    user_obj = await User.create(**user_info)
    new_user = await user_pydantic.from_tortoise_orm(user_obj)
    return {
        "status":"ok",
        "data":f"Hello {new_user.username}, thanks for choosingg our services, click the link to confirm registration."
    }

