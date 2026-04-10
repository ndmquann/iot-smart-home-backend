from fastapi import APIRouter, Depends, status
import asyncpg

from app.schemas.log import LogResponse
from app.db.database import get_db_connection
from app.crud import crud_log
from app.core.exceptions import LogException
from app.api.dependencies import get_current_user

router = APIRouter()

@router.get("/", response_model=list[LogResponse])
async def get_activity_history(
    limit: int = 50,
    curr_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Retrieve activity history logs for the user's home.
    
    Fetches the most recent activity logs (user actions, admin actions, etc.)
    for the home. Both admin and member users can view logs.
    
    Args:
        limit: Maximum number of log records to return (default: 50)
        curr_user: Current authenticated user
        conn: Async database connection
        
    Returns:
        list: List of LogResponse objects containing log details and timestamps
        
    Raises:
        LogException: If failed to retrieve activity history
    """
    try:
        home_id = curr_user['home_id']
        logs = await crud_log.get_recent_logs(conn, home_id, limit)
        return logs
    except Exception as e:
        raise LogException(detail=f"Failed to retrieve activity history: {str(e)}")