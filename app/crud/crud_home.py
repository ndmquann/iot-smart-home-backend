import asyncpg

async def create_home(conn: asyncpg.Connection, name: str) -> int:
    async with conn.transaction():
        query = """
            INSERT INTO homes (name)
            VALUES ($1)
            RETURNING id;
        """
        new_home_id = await conn.fetchval(query, name)
        return new_home_id