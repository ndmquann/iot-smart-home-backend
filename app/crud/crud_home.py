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
    
async def get_home_by_id(conn: asyncpg.Connection, home_id: int) -> dict |None:
    """
    Retrieve home details by home ID.
    
    Args:
        conn: Async database connection
        home_id: ID of the home to retrieve
        
    Returns:
        dict: Home details including id and name, or None if not found
    """
    query = """
        SELECT id, name
        FROM homes
        WHERE id = $1;
    """
    home_record = await conn.fetchrow(query, home_id)
    return dict(home_record) if home_record else None