import asyncpg

async def create_home(conn: asyncpg.Connection, name: str) -> int:
    """
    Create a new home in the database.
    
    Inserts a new home record and returns the generated home ID.
    
    Args:
        conn: Async database connection
        name: Name of the home
        
    Returns:
        int: ID of the newly created home
    """
    async with conn.transaction():
        query = """
            INSERT INTO homes (name)
            VALUES ($1)
            RETURNING id;
        """
        new_home_id = await conn.fetchval(query, name)
        return new_home_id