from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
import asyncpg

from app.db.database import get_db_connection
from app.core.security import verify_password, create_access_token
from app.crud import crud_user
from app.core.exceptions import UnauthorizedException

router = APIRouter()

@router.post("/login")
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """token login"""
    # 1. find user by email
    # form_data.username is standard OAuth2 for email
    user = await crud_user.get_user_by_email(conn, form_data.username)

    # 2. verify password
    if not user or not verify_password(form_data.password, user['password']):
        raise UnauthorizedException("Incorrect email or password")

    # 3. create token and return it
    access_token = create_access_token({"sub": user['email'], "role": user['type']})
    return {"access_token": access_token, "token_type": "bearer"}