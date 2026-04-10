from fastapi import APIRouter, Depends, status
import asyncpg

from app.db.database import get_db_connection
from app.schemas.user import UserCreate, UserResponse
from app.crud import crud_user, crud_home
from app.core.security import get_password_hash
from app.core.exceptions import BadRequestException, NotFoundException, DatabaseException

router = APIRouter()

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user: UserCreate,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Register a new user as Admin or Member.
    
    Creates a new user account with the specified role (admin or member). Automatically
    creates a new home if this is an admin user. Validates that email is not already registered.
    
    Args:
        user: UserCreate schema with fname, lname, email, password, type, home_name
        conn: Async database connection
        
    Returns:
        UserResponse: New user object with id, email, name, status, home_id, and type
        
    Raises:
        BadRequestException: If type is invalid, email already registered, or other validation fails
        DatabaseException: If database operations fail
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
        async with conn.transaction():
            # create home and get home_id
            home_id = await crud_home.create_home(conn, user.home_name)

            # hash password
            hashed_password = get_password_hash(user.password)

            # create user
            new_user = await crud_user.create_user(conn, user, hashed_password, home_id)
            return new_user
    except ValueError as e:
        raise BadRequestException(str(e))
    except Exception as e:
        raise DatabaseException(f"Failed to create user: {str(e)}")
    
@router.get("/{email}", response_model=UserResponse)
async def get_user(
    email: str,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Retrieve user information by email address.
    
    Fetches complete user details including role type, home assignment, and account status.
    
    Args:
        email: Email address of the user to retrieve
        conn: Async database connection
        
    Returns:
        UserResponse: User object with id, fname, lname, email, status, home_id, and type
        
    Raises:
        NotFoundException: If user with email not found
    """
    user = await crud_user.get_user_by_email(conn, email)
    if not user:
        raise NotFoundException(f"User with email {email} not found.")
    return user