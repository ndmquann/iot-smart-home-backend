from fastapi import APIRouter, Depends, status
import asyncpg

from app.db.database import get_db_connection
from app.schemas.user import UserCreate, UserResponse
from app.crud import crud_user
from app.core.exceptions import BadRequestException, NotFoundException, DatabaseException

router = APIRouter()

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user: UserCreate,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Register a new Admin or Member.
    """
    # 1. validate type 
    if user.type.lower() not in ["admin", "member"]:
        raise BadRequestException("Type must be either 'admin' or 'member'.")

    # 2. check if email exists
    existing_user = await crud_user.get_user_by_email(conn, user.email)
    if existing_user:
        raise BadRequestException("Email already registered.")

    # 3. insert user into db
    try:
        new_user = await crud_user.create_user(conn, user)
        return new_user
    except ValueError as e:
        raise BadRequestException(str(e))
    except Exception as e:
        raise DatabaseException(str(e))
    
@router.get("/{email}", response_model=UserResponse)
async def get_user(
    email: str,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Get user by email.
    """
    user = await crud_user.get_user_by_email(conn, email)
    if not user:
        raise NotFoundException(email)
    return user