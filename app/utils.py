import asyncpg

class Utils:
    async def get_admin_of_home(conn: asyncpg.Connection, home_id: int) -> int:
        query = """
            SELECT user_id
            FROM home_group_view
            WHERE home_id = $1;
        """
        admin_id = await conn.fetchval(query, home_id)
        return admin_id