import asyncpg
from app.schemas.user import UserCreate

async def create_user(conn: asyncpg.Connection, user: UserCreate, hashed_password: str, home_id: int) -> dict:
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
    query = "SELECT 1 FROM admins WHERE uid = $1;"
    record = await conn.fetchrow(query, user_id)
    return bool(record)