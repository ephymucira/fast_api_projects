from tortoise import Model,fields
from pydantic import BaseModel

class User(Model):
    id = fields.InteField(pk= True, index= True)
    username = fields.CharField(max_length=20, null = False, unique = True)
    email = fields.CharField(max_length=200, null = False, unique = True)
    password = fields.CharField(max_length = 100, null = False)
    is_verified = fields.BooleanField(default = False)