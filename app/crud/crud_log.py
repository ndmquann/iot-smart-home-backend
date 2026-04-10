import asyncpg
from app.schemas.log import LogBase

async def create_log(conn: asyncpg.Connection, log: LogBase) -> dict:
    """
    Create a new activity log entry in the database.
    
    Inserts a log record with type, description, and auto-generated timestamp.
    Logs track user actions, admin actions, and system events.
    
    Args:
        conn: Async database connection
        log: LogBase schema with type and description
        
    Returns:
        dict: New log object with id, type, description, and timestamp
    """
    async with conn.transaction():
        query = """
            INSERT INTO logs (type, description, home_id)
            VALUES ($1, $2, $3)
            RETURNING id, type, description, timestamp;
        """
        new_log = await conn.fetchrow(query, log.type, log.description, log.home_id)
        return dict(new_log)
    
# ==========================================
# FETCHING LOGS (For Module 4 UI)
# ==========================================
async def get_recent_logs(
        conn: asyncpg.Connection, 
        home_id: int,
        limit: int = 50) -> list[dict]:
    """
    fetch latest logs
    """
    query = """
        SELECT id, type, description, timestamp, home_id
        FROM logs
        WHERE home_id = $1
        ORDER BY timestamp DESC
        LIMIT $2;
    """
    records = await conn.fetch(query, home_id, limit)
    return [dict(record) for record in records]