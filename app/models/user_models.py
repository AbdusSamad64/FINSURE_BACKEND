from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Annotated

class UserSignup(BaseModel):
    name: Annotated[str, Field(min_length=2)]
    email: EmailStr
    password: Annotated[str, Field(min_length=4)]
    userType: Annotated[str, Field(pattern="^(freelancer|businessman)$")] 

class UserLogin(BaseModel):
    email: EmailStr
    password: str

