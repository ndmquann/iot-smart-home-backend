import asyncpg
from app.schemas.log import LogCreate
from app.crud import crud_log

class Utils:
    async def get_admin_of_home(conn: asyncpg.Connection, home_id: int) -> int:
        query = """
            SELECT user_id
            FROM home_group_view
            WHERE home_id = $1;
        """
        admin_id = await conn.fetchval(query, home_id)
        return admin_id
    
    async def generate_log(conn: asyncpg.Connection, description: str, type: str, home_id: int):
        log = LogCreate(
            type=type,
            description=description,
            home_id=home_id
        )
        await crud_log.create_log(conn, log)