from pydantic import BaseModel, EmailStr
from typing import Optional

# Shared properties
class UserBase(BaseModel):
    fname: str
    lname: str
    email: EmailStr
    home_id: str

# Properties required to create a user
class UserCreate(UserBase):
    password: str
    type: str # must be "admin" or "member

# Properties returned to client
class UserResponse(UserBase):
    id: int
    status: bool
    type: str