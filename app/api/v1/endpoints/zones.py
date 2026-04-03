from fastapi import APIRouter, Depends, status
import asyncpg

from app.db.database import get_db_connection
from app.schemas.zone import ZoneCreate, ZoneResponse
from app.crud import crud_zone
from app.api.dependencies import get_current_admin, get_current_user
from app.core.exceptions import DatabaseException, NotFoundException, BadRequestException
from app.utils import Utils

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
        new_zone = await crud_zone.create_zone(conn, zone, curr_admin['id'])

        admin = f"{curr_admin['fname']} {curr_admin['lname']}".title()
        description = f"{admin} created Room '{zone.room} ({zone.floor})'."
        await Utils.generate_log(conn, description, "admin action", curr_admin['home_id'])

        return new_zone
    except Exception as e:
        raise DatabaseException(f"Failed to create zone: {str(e)}")
    
@router.get("/", response_model=list[ZoneResponse])
async def read_all_zones(
    curr_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    get all zones to display on dashboard
    """
    zones = await crud_zone.get_all_zones(conn, curr_user['home_id'])
    if not zones:
        raise NotFoundException(f"Home ID {curr_user['home_id']} has no zones.")
    return zones

@router.get("/{floor}", response_model=list[ZoneResponse])
async def read_zones_by_floor(
    floor: int,
    curr_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    get all rooms in a floor
    """
    zones = await crud_zone.get_zone_by_floor(conn, floor, curr_user['home_id'])
    if not zones:
        raise NotFoundException(f"Floor {floor} not found in Home ID {curr_user['home_id']}.")
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
        raise NotFoundException(f"Zone ID {zone_id} not found in Home ID {curr_admin['home_id']}.")
    
    room = zone_info['room']
    floor = zone_info['floor']
    zone_display = f"{room} ({floor})" if floor else room

    admin = f"{curr_admin['fname']} {curr_admin['lname']}".title()
    description = f"{admin} deleted Room '{zone_display}'."
    await Utils.generate_log(conn, description, "admin action", curr_admin['home_id'])

    return {
        "message": f"Successfully deleted Room '{zone_display}'."
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
        raise NotFoundException(f"Floor {floor} not found in Home ID {curr_admin['home_id']}.")
    
    admin = f"{curr_admin['fname']} {curr_admin['lname']}".title()
    rooms = ", ".join(deleted_rooms)
    description = f"{admin} deleted Floor {floor} (removed rooms: {rooms})."

    await Utils.generate_log(conn, description, "admin action", curr_admin['home_id'])

    return {
        "message": f"Successfully deleted Floor {floor}.",
        "deleted_rooms": deleted_rooms
    }