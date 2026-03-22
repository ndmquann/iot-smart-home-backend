from fastapi import APIRouter, Depends, status
import asyncpg

from app.schemas.log import LogResponse
from app.db.database import get_db_connection
from app.crud import crud_log
from app.core.exceptions import LogException
from app.api.dependencies import get_current_user

router = APIRouter()

@router.get("/logs", response_model=list[LogResponse])
async def get_activity_history(
    limit: int = 50,
    curr_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    home_id = curr_user['home_id']
    logs = await crud_log.get_recent_logs(conn, home_id, limit)
    return logs

@router.post("/interact")
async def log_manual_interaction(
    user_id: int,
    controller_id: int,
    action: str,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        description = f"User turned {action} the device."
        new_log = await crud_log.log_user_action(conn, user_id, controller_id, description)
        return new_log
    except Exception as e:
        raise LogException(detail=f"Failed to log interaction: {str(e)}")
    
@router.post("/system-action")
async def log_automated_system_action(
    controller_id: int,
    schedule_id: int,
    action: str,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        description = f"System automatically turned {action} the device via schedule."
        new_log = await crud_log.log_system_trigger(
            conn=conn, 
            setting_id=schedule_id, 
            controller_id=controller_id, 
            description=description,
            log_type="system action"
        )
        return new_log
    except Exception as e:
        raise LogException(detail=f"Failed to log system action: {str(e)}")
    
@router.post("/sensor-alert")
async def log_sensor_threshold_alert(
    sensor_id: int,
    threshold_id: int,
    sensor_value: float,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        description = f"ALERT: Sensor reading ({sensor_value}) exceeded threshold."
        new_log = await crud_log.log_system_trigger(
            conn=conn, 
            setting_id=threshold_id, 
            device_id=sensor_id, 
            description=description,
            log_type="sensor alert"
        )
        return new_log
    except Exception as e:
        raise LogException(detail=f"Failed to log sensor alert: {str(e)}")