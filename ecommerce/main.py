from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise
from models import *
from authentications import *

#signals
from tortoise.signals import post_save
from typing import List, Optional,Type
from tortoise import BaseDBAsyncClient

app = FastAPI()


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


@app.get("/")
def index():
    return {"message":"Hello World"}



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

register_tortoise(

    app,
    db_url = "sqlite://database.sqlite3",
    modules = {"models":["models"]},
    generate_schemas = True,
    add_exception_handlers = True

)