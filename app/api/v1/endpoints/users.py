from fastapi import APIRouter, Depends, status
import asyncpg

from app.db.database import get_db_connection
from app.schemas.user import UserCreate, UserResponse, UserBase
from app.crud import crud_user, crud_home
from app.core.security import get_password_hash
from app.core.exceptions import BadRequestException, NotFoundException, DatabaseException
from app.api.dependencies import get_current_admin, get_current_user
from app.utils import Utils

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
            if user.type.lower() == "admin":
                # create home for admin
                if not user.home_name:
                    raise BadRequestException("Home name is required for admin registration.")
                home_id = await crud_home.create_home(conn, user.home_name)
            else:
                # for member, home_id must be provided and valid
                if not user.home_id:
                    raise BadRequestException("Home ID is required for member registration.")
                home = await crud_home.get_home_by_id(conn, user.home_id)
                if not home:
                    raise BadRequestException(f"Home with ID {user.home_id} does not exist.")
                home_id = user.home_id
            
            # hash password
            hashed_password = get_password_hash(user.password)
            
            # create user
            new_user_id = await crud_user.create_user(
                conn,
                user,
                hashed_password,
                home_id
            )
            return new_user_id
        
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

@router.delete("/{user_id}")
async def remove_user_from_home(
    user_id: int,
    conn: asyncpg.Connection = Depends(get_db_connection),
    curr_admin: dict = Depends(get_current_admin)
):
    """
    Delete a user from the database based on their user ID.
    
    Args:
        user_id: ID of the user to delete
        conn: Async database connection
        
    Returns:
        dict: User object with fname and lname if found, None otherwise
    """
    try:
        user_record = await crud_user.delete_user(conn, user_id, curr_admin['home_id'])
    except Exception as e:
        raise DatabaseException(f"Failed to remove user from home: {str(e)}")
    
    if not user_record:
        raise NotFoundException(f"User with ID {user_id} not found.")

    admin = f"{curr_admin['fname']} {curr_admin['lname']}".title()
    user = f"{user_record['fname']} {user_record['lname']}".title()
    description = f"{admin} removed user {user} from home."
    await Utils.generate_log(conn, description, "admin action", curr_admin['home_id'])

    return {
        "message": f"Successfully removed {user} from home."
    }

@router.get("/home/members")
async def get_home_members(
    curr_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Retrieve all members in a home.
    
    Args:
        curr_user: Current authenticated user
        conn: Async database connection
        
    Returns:
        list: List of UserResponse objects for members in the home
    """
    members = await crud_user.view_home_member(conn, curr_user['home_id'])
    return members

@router.put("/{user_id}")
async def update_user_info(
    new_user: UserBase,
    curr_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Update user information.
    
    Args:
        new_user: UserBase schema with updated values
        curr_user: Current authenticated user
        conn: Async database connection
        
    Returns:
        dict: Success message
    """
    await crud_user.update_user_info(conn, curr_user['id'], new_user)
    return {"message": "Successfully updated user information."}