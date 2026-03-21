from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
import asyncpg
import jwt
from jwt.exceptions import InvalidTokenError

from app.db.database import get_db_connection
from app.core.config import settings
from app.crud import crud_user
from app.core.exceptions import UnauthorizedException

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    credentials_exception = UnauthorizedException("Could not validate credentials")

    try:
        # decode the token
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    
    # verify the user actually in the db
    user = await crud_user.get_user_by_email(conn, email)
    if user is None:
        raise credentials_exception
    return user

async def get_current_admin(
    current_user: dict = Depends(get_current_user)
):
    if current_user['type'] != 'admin':
        raise UnauthorizedException("Admin only.")
    return current_user