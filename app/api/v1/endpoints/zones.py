from fastapi import APIRouter, Depends, status
import asyncpg

from app.db.database import get_db_connection
from app.schemas.zone import ZoneCreate, ZoneResponse
from app.crud import crud_zone, crud_log
from app.api.dependencies import get_current_admin
from app.core.exceptions import DatabaseException, NotFoundException, BadRequestException

router = APIRouter()

@router.post("/", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
async def create_new_zone(
    zone: ZoneCreate,
    curr_admin: dict = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    create a new zone
    """
    try:
        admin_id = curr_admin['id']
        new_zone = await crud_zone.create_zone(conn, zone, admin_id)
        return new_zone
    except Exception as e:
        raise DatabaseException(f"Failed to create zone: {str(e)}")
    
@router.get("/", response_model=list[ZoneResponse])
async def read_all_zones(
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    get all zones to display on dashboard
    """
    zones = await crud_zone.get_all_zones(conn)
    return zones

@router.get("/{floor}", response_model=list[ZoneResponse])
async def read_zones_by_floor(
    floor: int,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    get all rooms in a floor
    """
    zones = await crud_zone.get_zone_by_floor(conn, floor)
    if not zones:
        raise NotFoundException(floor)
    return zones

@router.delete("/{zone_id}")
async def remove_zone(
    zone_id: int,
    curr_admin: dict = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        zone_info = await crud_zone.delete_zone(conn, zone_id)
    except Exception as e:
        raise BadRequestException(str(e))
    
    if not zone_info:
        raise NotFoundException(zone_id)
    
    room = zone_info['room']
    floor = zone_info['floor']
    zone_display = f"{room} ({floor})" if floor else room

    await crud_log.log_admin_delete_action(
        conn=conn,
        admin_name=f"{curr_admin['fname']} {curr_admin['lname']}",
        description=f"deleted zone {zone_display}."
    )

    return {
        "message": f"Successfully deleted '{zone_display}'."
    }

@router.delete("/floor/{floor}")
async def remove_floor(
    floor: int,
    curr_admin: dict = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        deleted_rooms = await crud_zone.delete_floor(conn, floor)
    except Exception as e:
        raise BadRequestException(str(e))
    
    if not deleted_rooms:
        raise NotFoundException(floor)
    
    rooms = ", ".join(deleted_rooms)
    log_description = f"deleted floor {floor} (removed rooms: {rooms})."

    await crud_log.log_admin_delete_action(
        conn=conn,
        admin_name=f"{curr_admin['fname']} {curr_admin['lname']}",
        description=log_description
    )

    return {
        "message": f"Successfully deleted floor {floor}.",
        "deleted_rooms": deleted_rooms
    }