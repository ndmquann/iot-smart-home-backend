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
    Create a new zone (room) in the home.
    
    Creates a new zone (room) on a specified floor. Only admins can create zones.
    This action generates an admin log entry.
    
    Args:
        zone: ZoneCreate schema with room name and floor number
        curr_admin: Current authenticated admin user
        conn: Async database connection
        
    Returns:
        ZoneResponse: New zone object with id, admin_id, floor, and room name
        
    Raises:
        DatabaseException: If zone creation fails
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
    Retrieve all zones (rooms) in the user's home.
    
    Fetches all zones organized by floor and room name. Both admins and members can view zones.
    
    Args:
        curr_user: Current authenticated user
        conn: Async database connection
        
    Returns:
        list: List of ZoneResponse objects with id, floor, room name, and admin_id
        
    Raises:
        NotFoundException: If home has no zones
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
    Retrieve all rooms on a specific floor.
    
    Fetches all zones for a given floor in the user's home, ordered by room name.
    
    Args:
        floor: Floor number to retrieve rooms from
        curr_user: Current authenticated user
        conn: Async database connection
        
    Returns:
        list: List of ZoneResponse objects for the specified floor
        
    Raises:
        NotFoundException: If floor not found or has no rooms
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
    """
    Delete a zone (room) from the system.
    
    Permanently removes a zone record. Can only delete zones with no devices attached.
    Only admins can delete zones. This action generates an admin log entry.
    
    Args:
        zone_id: ID of the zone to delete
        curr_admin: Current authenticated admin user
        conn: Async database connection
        
    Returns:
        dict: Success message with zone details (room and floor)
        
    Raises:
        NotFoundException: If zone not found
        BadRequestException: If zone still has devices attached
    """
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
    """
    Delete all rooms on a specific floor.
    
    Permanently removes all zones on a given floor. Can only delete if no devices
    are attached to any rooms on that floor. Only admins can delete floors.
    This action generates an admin log entry with list of deleted rooms.
    
    Args:
        floor: Floor number to delete
        curr_admin: Current authenticated admin user
        conn: Async database connection
        
    Returns:
        dict: Success message and list of deleted room names
        
    Raises:
        NotFoundException: If floor or rooms not found
        BadRequestException: If rooms on floor still have devices attached
    """
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