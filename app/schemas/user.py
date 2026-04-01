from pydantic import BaseModel, EmailStr
from typing import Optional

# Shared properties
class UserBase(BaseModel):
    fname: str
    lname: str
    email: EmailStr

# Properties required to create a user
class UserCreate(UserBase):
    password: str
    type: str # must be "admin" or "member
    home_name: Optional[str] = None # only used for registration, ignored for login

# Properties returned to client
class UserResponse(UserBase):
    id: int
    status: bool
    type: str
    home_id: int

    class Config:
        from_attributes = True