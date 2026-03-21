import asyncpg
from app.schemas.user import UserCreate
from app.core.security import get_password_hash

async def create_user(conn: asyncpg.Connection, user: UserCreate) -> dict:
    async with conn.transaction():
        query_base_user = """
            INSERT INTO users (fname, lname, email, password)
            VALUES ($1, $2, $3, $4)
            RETURNING id, fname, lname, email, status;
        """

        new_user_record = await conn.fetchrow(
            query_base_user, 
            user.fname, 
            user.lname, 
            user.email, 
            get_password_hash(user.password)
        )
        
        user_id = new_user_record['id']

        if user.type == "admin":
            await conn.execute(
                "INSERT INTO admins (uid) VALUES ($1);", user_id
            )
        elif user.type == "member":
            await conn.execute(
                "INSERT INTO members (uid) VALUES ($1);", user_id
            )

        result = dict(new_user_record)
        result['type'] = user.type
        return result
        
async def get_user_by_email(conn: asyncpg.Connection, email: str) -> dict | None:
    """
    call when user login with email to get user's info and role
    """
    query = """
        SELECT 
            u.id, u.fname, u.lname, u.email, u.status
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
    query = "SELECT 1 FROM admins WHERE uid = $1;"
    record = await conn.fetchrow(query, user_id)
    return bool(record)