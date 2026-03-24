from fastapi import APIRouter, Depends, status
import asyncpg

from app.db.database import get_db_connection
from app.schemas.setting import ScheduleCreate, ScheduleResponse, ThresholdCreate, ThresholdResponse
from app.crud import crud_setting, crud_log
from app.api.dependencies import get_current_admin
from app.core.exceptions import DatabaseException, BadRequestException, NotFoundException

router = APIRouter()

@router.post("/schedules", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_new_schedule(
    schedule: ScheduleCreate,
    curr_admin: dict = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    create a new schedule
    """
    try:
        admin_id = curr_admin['id']
        new_schedule = await crud_setting.create_schedule(conn, schedule)
        await crud_log.log_admin_config(conn, admin_id, new_schedule['sid'], f"Created schedule {schedule.name}")
        return new_schedule
    except Exception as e:
        raise DatabaseException(f"Failed to create schedule: {str(e)}")
    
@router.get("/schedules", response_model=list[ScheduleResponse])
async def read_all_schedules(
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    fetch all schedules
    """
    schedules = await crud_setting.get_all_schedules(conn)
    return schedules

@router.post("/schedules/{schedule_id}/apply/{controller_id}")
async def apply_schedule_to_controller(
    schedule_id: int, # schedule id
    controller_id: int, # controller id
    curr_admin: dict = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        admin_id = curr_admin['id']
        await crud_setting.apply_schedule_to_controller(conn, schedule_id, controller_id)
        await crud_log.log_admin_config(conn, admin_id, schedule_id, f"Applied schedule to controller {controller_id}")
    except Exception as e:
        raise BadRequestException("Failed to apply schedule. Ensure IDs exist.")
    
@router.post("/thresholds", response_model=ThresholdResponse, status_code=status.HTTP_201_CREATED)
async def create_new_threshold(
    threshold: ThresholdCreate,
    curr_admin: dict = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    create a new threshold
    """
    try:
        admin_id = curr_admin['id']
        new_threshold = await crud_setting.create_threshold(conn, threshold)
        await crud_log.log_admin_config(conn, admin_id, new_threshold['sid'], f"Created threshold {threshold.name}")
        return new_threshold
    except Exception as e:
        raise DatabaseException(f"Failed to create threshold: {str(e)}")
    
@router.get("/thresholds", response_model=list[ThresholdResponse])
async def read_all_thresholds(
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    fetch all thresholds
    """
    thresholds = await crud_setting.get_all_thresholds(conn)
    return thresholds

@router.post("/thresholds/{threshold_id}/apply/{sensor_id}")
async def apply_threshold_to_sensor(
    threshold_id: int, # threshold
    sensor_id: int, # sensor
    curr_admin: dict = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        admin_id = curr_admin['id']
        await crud_setting.apply_threshold_to_sensor(conn, threshold_id, sensor_id)
        await crud_log.log_admin_config(
            conn, 
            admin_id, 
            threshold_id, 
            f"Applied threshold to sensor {sensor_id}")
    except Exception as e:
        raise BadRequestException("Failed to apply threshold. Ensure IDs exist.")
    
@router.delete("/{setting_id}/")
async def remove_setting(
    setting_id: int,
    curr_admin: dict = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    setting_name = await crud_setting.delete_setting(conn, setting_id)
    if not setting_name:
        raise NotFoundException(setting_id)
    
    await crud_log.log_admin_delete_action(
        conn=conn, 
        admin_name=f"{curr_admin['fname']} {curr_admin['lname']}", 
        home_id=curr_admin['home_id'],
        description=f"deleted setting cofiguration {setting_name}."
    )

    return {
        "message": f"Successfully deleted '{setting_name}'."
    }