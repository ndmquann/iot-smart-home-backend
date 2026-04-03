from fastapi import APIRouter, Depends, status
import asyncpg

from app.db.database import get_db_connection
from app.schemas.setting import ScheduleCreate, ScheduleResponse, ThresholdCreate, ThresholdResponse
from app.crud import crud_setting
from app.api.dependencies import get_current_admin, get_current_user
from app.core.exceptions import DatabaseException, BadRequestException, NotFoundException
from app.utils import Utils

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
        new_schedule = await crud_setting.create_schedule(conn, schedule, curr_admin['id'])

        admin = f"{curr_admin['fname']} {curr_admin['lname']}".title()
        description = f"{admin} created Schedule '{schedule.name}'."
        await Utils.generate_log(conn, description, "admin action", curr_admin['home_id'])
        
        return new_schedule
    except Exception as e:
        raise DatabaseException(f"Failed to create schedule: {str(e)}")
    
@router.get("/schedules", response_model=list[ScheduleResponse])
async def read_all_schedules(
    conn: asyncpg.Connection = Depends(get_db_connection),
    curr_user: dict = Depends(get_current_user)
):
    """
    fetch all schedules availabe to the user (admin and member can view schedules)
    """
    schedules = await crud_setting.get_all_schedules(conn, curr_user['home_id'])
    if not schedules:
        raise NotFoundException(f"Home ID {curr_user['home_id']} has no schedules.")
    
    return schedules

@router.get("/schedules/{setting_id}")
async def read_schedule(
    setting_id: int,
    conn: asyncpg.Connection = Depends(get_db_connection),
    curr_user: dict = Depends(get_current_user)
):
    """
    fetch a specific schedule by its setting ID
    """
    schedule = await crud_setting.get_schedule_by_id(conn, setting_id)
    if not schedule:
        raise NotFoundException(f"Schedule with ID {setting_id} not found.")
    
    return schedule

@router.put("/schedules/{setting_id}")
async def update_schedule(
    setting_id: int,
    schedule: ScheduleCreate,
    curr_admin: dict = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    update an existing schedule
    """
    setting = await crud_setting.get_schedule_by_id(conn, setting_id)
    if not setting:
        raise NotFoundException(f"Schedule with ID {setting_id} not found.")
    
    await crud_setting.update_schedule(conn, setting_id, schedule.name, schedule, curr_admin['id'])

    admin = f"{curr_admin['fname']} {curr_admin['lname']}".title()
    description = f"{admin} updated Schedule '{schedule.name}'."
    await Utils.generate_log(conn, description, "admin action", curr_admin['home_id'])

    return {
        "message": f"Successfully updated Schedule '{schedule.name}'."
    }


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
        new_threshold = await crud_setting.create_threshold(conn, threshold, curr_admin['id'])

        admin = f"{curr_admin['fname']} {curr_admin['lname']}".title()
        description = f"{admin} created Threshold '{threshold.name}'."
        await Utils.generate_log(conn, description, "admin action", curr_admin['home_id'])

        return new_threshold
    except Exception as e:
        raise DatabaseException(f"Failed to create threshold: {str(e)}")
    
@router.get("/thresholds", response_model=list[ThresholdResponse])
async def read_all_thresholds(
    curr_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    fetch all thresholds
    """
    thresholds = await crud_setting.get_all_thresholds(conn, curr_user['home_id'])
    if not thresholds:
        raise NotFoundException(f"Home ID {curr_user['home_id']} has no thresholds.")
    
    return thresholds

@router.get("/thresholds/{setting_id}")
async def read_threshold(
    setting_id: int,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    fetch a specific threshold by its setting ID
    """
    threshold = await crud_setting.get_threshold_by_id(conn, setting_id)
    if not threshold:
        raise NotFoundException(f"Threshold with ID {setting_id} not found.")
    
    return threshold

@router.put("/thresholds/{setting_id}")
async def update_threshold(
    setting_id: int,
    threshold: ThresholdCreate,
    curr_admin: dict = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    update an existing threshold
    """
    setting = await crud_setting.get_threshold_by_id(conn, setting_id)
    if not setting:
        raise NotFoundException(f"Threshold with ID {setting_id} not found.")
    
    await crud_setting.update_threshold(conn, setting_id, threshold.name, threshold, curr_admin['id'])

    admin = f"{curr_admin['fname']} {curr_admin['lname']}".title()
    description = f"{admin} updated Threshold '{threshold.name}'."
    await Utils.generate_log(conn, description, "admin action", curr_admin['home_id'])

    return {
        "message": f"Successfully updated Threshold '{threshold.name}'."
    }

@router.delete("/{setting_id}")
async def remove_setting(
    setting_id: int,
    curr_admin: dict = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    setting_name = await crud_setting.delete_setting(conn, setting_id)
    if not setting_name:
        raise NotFoundException(f"Setting ID {setting_id} not found.")
    
    admin = f"{curr_admin['fname']} {curr_admin['lname']}".title()
    description = f"{admin} deleted setting '{setting_name}'."
    await Utils.generate_log(conn, description, "admin action", curr_admin['home_id'])

    return {
        "message": f"Successfully deleted '{setting_name}'."
    }