import asyncpg
from app.schemas.user import UserCreate

async def create_user(conn: asyncpg.Connection, user: UserCreate, hashed_password: str, home_id: int) -> dict:
    """
    Create a new user in the database and assign user type (admin or member).
    
    Inserts a new user record into the users table with hashed password,
    then inserts corresponding record into admins or members table based on user type.
    
    Args:
        conn: Async database connection
        user: UserCreate schema with fname, lname, email, password, type, home_name
        hashed_password: Pre-hashed password string
        home_id: ID of the home this user belongs to
        
    Returns:
        dict: New user object with id, fname, lname, email, status, home_id, and type
    """
    async with conn.transaction():
        query_base_user = """
            INSERT INTO users (fname, lname, email, password, home_id)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, fname, lname, email, status, home_id;
        """

        record = await conn.fetchrow(
            query_base_user, 
            user.fname, 
            user.lname, 
            user.email, 
            hashed_password,
            home_id
        )
        
        new_user = dict(record)
        user_id = new_user['id']
        user_type = user.type.lower()

        if user_type == "admin":
            await conn.execute(
                "INSERT INTO admins (uid) VALUES ($1);", user_id
            )
        elif user_type == "member":
            await conn.execute(
                "INSERT INTO members (uid) VALUES ($1);", user_id
            )

        new_user['type'] = user_type
        return new_user
        
async def get_user_by_email(conn: asyncpg.Connection, email: str) -> dict | None:
    """
    call when user login with email to get user's info and role
    """
    query = """
        SELECT 
            u.id, u.fname, u.lname, u.email, u.password, u.status, u.home_id,
            CASE 
                WHEN a.uid IS NOT NULL THEN 'admin'
                WHEN m.uid IS NOT NULL THEN 'member'
            END AS type
        FROM users u
        LEFT JOIN admins a ON u.id = a.uid
        LEFT JOIN members m ON u.id = m.uid
        WHERE u.email = $1;
    """
    record = await conn.fetchrow(query, email)
    return dict(record) if record else None

async def is_admin(conn: asyncpg.Connection, user_id: int) -> bool:
    """
    Check if a user has admin privileges.
    
    Queries the admins table to verify if the user ID exists as an admin.
    
    Args:
        conn: Async database connection
        user_id: ID of the user to check
        
    Returns:
        bool: True if user is an admin, False otherwise
    """
    query = "SELECT 1 FROM admins WHERE uid = $1;"
    record = await conn.fetchrow(query, user_id)
    return bool(record)

async def delete_user(conn: asyncpg.Connection, user_id: int, home_id: int) -> dict | None:
    """
    Delete a user from the database based on their user ID and home ID.
    
    Permanently removes a user record. Validation ensures there is at least one admin in the home.
    
    Args:
        conn: Async database connection
        user_id: ID of the user to delete
        home_id: ID of the home the user belongs to
        
    Returns:
        dict: User object with fname and lname if found, None otherwise
    """
    number_admin = """
        SELECT COUNT(*)
        FROM home_group_view
        WHERE home_id = $1 AND user_type = 'admin';
    """
    record = await conn.fetchrow(number_admin, home_id)
    if record[0] == 1:
        raise Exception("Cannot delete last admin.")
    
    query = """
        DELETE FROM users
        WHERE id = $1 AND home_id = $2
        RETURNING fname, lname;
    """
    record = await conn.fetchrow(query, user_id, home_id)
    return dict(record) if record else None

async def view_home_member(conn: asyncpg.Connection, home_id: int):
    query = """
        SELECT * FROM home_group_view
        WHERE home_id = $1;
    """
    records = await conn.fetch(query, home_id)
    return [dict(record) for record in records]