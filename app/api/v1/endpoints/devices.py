from fastapi import APIRouter, Depends, status
import asyncpg

from app.db.database import get_db_connection
from app.schemas.device import DeviceCreate, DeviceResponse
from app.crud import crud_device, crud_log, crud_user
from app.api.dependencies import get_current_admin, get_current_user
from app.core.exceptions import BadRequestException, NotFoundException, UnauthorizedException, DatabaseException

from app.services import mqtt as mqtt_service

router = APIRouter()

@router.post("/", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def register_new_device(
    device: DeviceCreate,
    curr_admin: int = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    register a new device and categorize it as a sensor or controller
    """
    if device.type not in ["sensor", "controller"]:
        raise BadRequestException("Device type must be either 'sensor' or 'controller'.")
    
    try:
        admin_id = curr_admin['id']
        new_device = await crud_device.create_device(conn, device, admin_id)
        await crud_log.log_admin_registry(
            conn=conn,
            home_id=curr_admin['home_id'],
            description=f"{curr_admin['fname']} {curr_admin['lname']} created {device.type} {device.name}."
        )
        return new_device
    except Exception as e:
        raise DatabaseException(f"Failed to create device: {str(e)}")
    
@router.get("/", response_model=list[DeviceResponse])
async def read_all_devices(
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    get all devices to display on dashboard
    """
    devices = await crud_device.get_all_devices(conn)
    return devices

@router.post("/{device_id}/toggle")
async def toggle_device(
    device_id: int,
    action: str, # 'on' or 'off'
    curr_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    # verify action
    if action.lower() not in ["on", "off"]:
        raise BadRequestException("Action must be either 'on' or 'off'.")
    
    # verify device
    device = await crud_device.get_device_by_id(conn, device_id)
    if not device:
        raise NotFoundException(device_id)
    
    # check device's type
    device_type_info = await crud_device.get_device_by_feed_id(conn, device['feed_id'])
    device_type = device_type_info['type'] if device_type_info else 'unknown'
    
    if device_type == 'sensor':
        # only admin can toggle sensor
        admin_check = await crud_user.is_admin(conn, curr_user['id'])
        if not admin_check:
            raise UnauthorizedException("Access Denied: Only admins can control sensors.")
    elif device_type != 'controller':
        raise BadRequestException("Unrecognized device type.")
    
    feed_id = f"{device['feed_id']}-control" if device_type == 'controller' else device['feed_id']
    
    mqtt_value = '1' if action.lower() == 'on' else '0'
    mqtt_service.publish_command(feed_id, mqtt_value)

    description = f"User manually turned {action} the {device_type}: {device['name']}."
    await crud_log.log_user_action(
        conn=conn, 
        user_id=curr_user['id'], 
        device_id=device_id, 
        description=description,
        home_id=curr_user['home_id']
        )
    
    return {
        "message": f"Successfully sent {action} command to {device['name']}.",
        "feed_id": feed_id
    }

@router.post("/{device_id}/mode")
async def set_device_mode(
    device_id: int,
    mode: str, # 'manual' or 'auto'
    curr_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    if mode.lower() not in ["manual", "auto"]:
        raise BadRequestException("Mode must be either 'manual' or 'auto'.")
    
    device = await crud_device.get_device_by_id(conn, device_id)
    if not device:
        raise NotFoundException(device_id)
    
    device_type_info = await crud_device.get_device_by_feed_id(conn, device['feed_id'])
    if not device_type_info or device_type_info['type'] != 'controller':
        raise BadRequestException("Only controllers support setting modes.")
    
    await crud_device.update_controller_mode(conn, device_id, mode.lower())

    await crud_log.log_user_action(
        conn=conn, 
        user_id=curr_user['id'], 
        device_id=device_id, 
        description=f"User set {device['name']}'s mode to {mode.upper()}.",
        home_id=curr_user['home_id']
    )

    return {
        "message": f"Successfully set {device['name']}'s mode to {mode.upper()}."
    }

@router.post("/{device_id}/speed")
async def set_device_speed(
    device_id: int,
    speed: int,
    curr_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    if speed < 0 or speed > 100:
        raise BadRequestException("Speed must be between 0 and 100.")
    
    device = await crud_device.get_device_by_id(conn, device_id)
    if not device:
        raise NotFoundException(device_id)
    
    device_type_info = await crud_device.get_device_by_feed_id(conn, device['feed_id'])
    if not device_type_info or device_type_info['type'] != 'controller':
        raise BadRequestException("Only controllers support setting speeds.")
    
    await crud_device.update_controller_speed(conn, device_id, speed)

    feed_id = f"{device['feed_id']}-speed"
    mqtt_service.publish_command(feed_id, str(speed))

    await crud_log.log_user_action(
        conn=conn, 
        user_id=curr_user['id'], 
        device_id=device_id, 
        description=f"User set {device['name']}'s speed to {speed}.",
        home_id=curr_user['home_id']
    )

    return {
        "message": f"Successfully set {device['name']}'s speed to {speed}.",
        "feed_id": feed_id
    }

@router.delete("/{device_id}/")
async def remove_device(
    device_id: int,
    curr_admin: dict = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    device_name = await crud_device.delete_device(conn, device_id)
    if not device_name:
        raise NotFoundException(device_id)
    
    await crud_log.log_admin_delete_action(
        conn=conn, 
        admin_name=f"{curr_admin['fname']} {curr_admin['lname']}", 
        home_id=curr_admin['home_id'],
        description=f"deleted device {device_name}."
    )

    return {
        "message": f"Successfully deleted '{device_name}'."
    }

@router.get("/{device_id}/value")
async def read_device_state(
    device_id: int,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    get device state for display
    """
    device = await crud_device.read_device_detail(conn, device_id)
    if not device:
        raise NotFoundException(device_id)
    return device  