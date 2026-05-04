from fastapi import APIRouter, Depends, status, Query
from typing import List
import asyncpg

from app.db.database import get_db_connection
from app.schemas.device import DeviceCreate, DeviceResponse, SensorHistoryResponse, DeviceBase
from app.crud import crud_device, crud_user
from app.api.dependencies import get_current_admin, get_current_user
from app.core.exceptions import BadRequestException, NotFoundException, UnauthorizedException, DatabaseException
from app.services import mqtt as mqtt_service
from app.utils import Utils

router = APIRouter()

@router.post("/", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def register_new_device(
    device: DeviceCreate,
    curr_admin: int = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Register a new device as a sensor or controller.
    
    Creates a new device and categorizes it as either a sensor (for reading data)
    or a controller (for performing actions). Only admins can create devices.
    This action generates an admin log entry.
    
    Args:
        device: DeviceCreate schema with name, zone_id, feed_id, status, type
        curr_admin: Current authenticated admin user
        conn: Async database connection
        
    Returns:
        DeviceResponse: New device object with id, name, zone_id, feed_id, status, and type
        
    Raises:
        BadRequestException: If device type is not 'sensor' or 'controller'
        DatabaseException: If device creation fails
    """
    if device.type not in ["sensor", "controller"]:
        raise BadRequestException("Device type must be either 'sensor' or 'controller'.")
    
    try:
        new_device = await crud_device.create_device(conn, device, curr_admin['id'])

        admin = f"{curr_admin['fname']} {curr_admin['lname']}".title()
        description = f"{admin} created {device.type.capitalize()} '{device.name}'."
        await Utils.generate_log(conn, description, "admin action", curr_admin['home_id'])

        return new_device
    except Exception as e:
        raise DatabaseException(f"Failed to create device: {str(e)}")
    
@router.get("/", response_model=list[DeviceResponse])
async def read_all_devices(
    curr_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Retrieve all devices in the user's home.
    
    Fetches all devices (sensors and controllers) for the user's home, including
    current status and sensor values. Results are ordered by zone and device name.
    Both admins and members can view devices.
    
    Args:
        curr_user: Current authenticated user
        conn: Async database connection
        
    Returns:
        list: List of DeviceResponse objects with details for display on dashboard
        
    Raises:
        NotFoundException: If home has no devices
    """
    devices = await crud_device.get_all_devices(conn, curr_user['home_id'])
    if not devices:
        raise NotFoundException(f"Home ID {curr_user['home_id']} has no devices.")
    return devices

@router.post("/{device_id}/toggle")
async def toggle_device(
    device_id: int,
    action: str, # 'on' or 'off'
    curr_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Toggle a device on or off by sending MQTT command.
    
    Sends an on/off command to a device via MQTT. Admins can control both sensors
    and controllers, while members can only control controllers.
    
    Args:
        device_id: ID of the device to toggle
        action: 'on' or 'off' command
        curr_user: Current authenticated user
        conn: Async database connection
        
    Returns:
        dict: Success message and the MQTT feed ID
        
    Raises:
        BadRequestException: If action is not 'on' or 'off'
        NotFoundException: If device not found
        UnauthorizedException: If non-admin tries to control a sensor
    """
    # verify action
    if action.lower() not in ["on", "off"]:
        raise BadRequestException("Action must be either 'on' or 'off'.")
    
    # verify device
    device = await crud_device.get_device_by_id(conn, device_id)
    if not device:
        raise NotFoundException(f"Device ID {device_id} not found.")
    
    # check device's type
    device_type = device['type']
    
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

    user = f"{curr_user['fname']} {curr_user['lname']}".title()
    description = f"{user} manually turned {action.upper()} the {device_type.capitalize()}: {device['name']}."
    await Utils.generate_log(conn, description, "user action", curr_user['home_id'])
    
    return {
        "message": f"Successfully sent {action.upper()} command to {device['name']}.",
        "feed_id": feed_id
    }

@router.post("/{device_id}/mode")
async def set_device_mode(
    device_id: int,
    mode: str, # 'manual' or 'auto'
    curr_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Set controller device mode to automatic or manual.
    
    Changes the operational mode of a controller device. Only controllers support
    mode switching; sensors do not have mode settings.
    
    Args:
        device_id: ID of the controller device
        mode: 'manual' or 'auto' mode
        curr_user: Current authenticated user
        conn: Async database connection
        
    Returns:
        dict: Success message with the new mode
        
    Raises:
        BadRequestException: If mode is invalid or device is not a controller
        NotFoundException: If device not found
    """
    if mode.lower() not in ["manual", "auto"]:
        raise BadRequestException("Mode must be either 'manual' or 'auto'.")
    
    device = await crud_device.get_device_by_id(conn, device_id)
    if not device:
        raise NotFoundException(f"Device ID {device_id} not found.")
    
    device_type = device['type']
    if device_type != 'controller':
        raise BadRequestException("Only controllers support setting modes.")
    
    await crud_device.update_controller_mode(conn, device_id, mode.lower())
    
    feed_id = f"{device['feed_id']}-mode"
    dmode = '0' if mode.lower() == 'auto' else '1'
    mqtt_service.publish_command(feed_id, dmode)

    user = f"{curr_user['fname']} {curr_user['lname']}".title()
    description = f"{user} set {device['name']}'s mode to {mode.upper()}."
    await Utils.generate_log(conn, description, "user action", curr_user['home_id'])

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
    """
    Set controller device speed level (0-100).
    
    Adjusts the speed or power level of a controller device via MQTT command.
    Only controllers support speed adjustment; sensors do not have speed settings.
    
    Args:
        device_id: ID of the controller device
        speed: Speed value between 0 and 100
        curr_user: Current authenticated user
        conn: Async database connection
        
    Returns:
        dict: Success message, speed value, and MQTT feed ID
        
    Raises:
        BadRequestException: If speed is outside 0-100 range or device is not a controller
        NotFoundException: If device not found
    """
    if speed < 0 or speed > 100:
        raise BadRequestException("Speed must be between 0 and 100.")
    
    device = await crud_device.get_device_by_id(conn, device_id)
    if not device:
        raise NotFoundException(f"Device ID {device_id} not found.")
    
    device_type = device['type']
    if device_type != 'controller':
        raise BadRequestException("Only controllers support setting speeds.")
    
    await crud_device.update_controller_speed(conn, device_id, speed)

    feed_id = f"{device['feed_id']}-speed"
    mqtt_service.publish_command(feed_id, str(speed))

    user = f"{curr_user['fname']} {curr_user['lname']}".title()
    description = f"{user} set {device['name']}'s speed to {speed}."
    await Utils.generate_log(conn, description, "user action", curr_user['home_id'])

    return {
        "message": f"Successfully set {device['name']}'s speed to {speed}.",
        "feed_id": feed_id
    }

@router.delete("/{device_id}")
async def remove_device(
    device_id: int,
    curr_admin: dict = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Delete a device from the system.
    
    Permanently removes a device record from the database. Only admins can delete devices.
    This action also generates an admin log entry.
    
    Args:
        device_id: ID of the device to delete
        curr_admin: Current authenticated admin user
        conn: Async database connection
        
    Returns:
        dict: Success message with device name
        
    Raises:
        NotFoundException: If device not found
    """
    device_name = await crud_device.delete_device(conn, device_id)
    if not device_name:
        raise NotFoundException(f"Device ID {device_id} not found.")
    
    admin = f"{curr_admin['fname']} {curr_admin['lname']}".title()
    description = f"{admin} deleted device '{device_name}'."
    await Utils.generate_log(conn, description, "admin action", curr_admin['home_id'])

    return {
        "message": f"Successfully deleted '{device_name}'."
    }

@router.get("/{device_id}/state")
async def read_device_state(
    device_id: int,
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Retrieve the current state of a device.
    
    Fetches comprehensive device details including type-specific information (sensor value,
    controller mode/speed), zone, feed ID, and current status.
    
    Args:
        device_id: ID of the device to retrieve state for
        conn: Async database connection
        
    Returns:
        dict: Device state object with all current details
        
    Raises:
        NotFoundException: If device not found
    """
    device = await crud_device.read_device_detail(conn, device_id)
    if not device:
        raise NotFoundException(f"Device ID {device_id} not found.")
    return device  

@router.get("/{device_id}/history", response_model=List[SensorHistoryResponse])
async def read_device_history(
    device_id: int,
    limit: int = Query(50, description="Number of records to return."),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Retrieve historical data for a sensor device.
    
    Fetches time-series sensor readings with timestamps. Only works for sensor devices;
    controller devices do not have history data.
    
    Args:
        device_id: ID of the sensor device
        limit: Maximum number of historical records to return (default: 50)
        conn: Async database connection
        
    Returns:
        list: List of SensorHistoryResponse objects with value and timestamp
        
    Raises:
        NotFoundException: If device not found
        BadRequestException: If device is not a sensor
    """
    device = await crud_device.read_device_detail(conn, device_id)
    if not device:
        raise NotFoundException(f"Device ID {device_id} not found.")
    
    if device['type'] != 'sensor':
        raise BadRequestException("Only sensors support history.")
    
    history = await crud_device.get_sensor_history(conn, device_id, limit)
    return history

@router.put("/{device_id}")
async def update_device_details(
    device_id: int,
    new_device: DeviceBase,
    curr_admin: dict = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    """
    Update device details (name, zone_id, feed_id).
    
    This action generates an admin log entry.
    
    Args:
        device_id: ID of the device to update
        new_device: DeviceBase schema with name, zone_id, feed_id
        curr_admin: Current authenticated admin user
        conn: Async database connection
        
    Returns:
        dict: Success message with updated device details
        
    Raises:
        NotFoundException: If device not found
    """
    device = await crud_device.read_device_detail(conn, device_id)
    if not device:
        raise NotFoundException(f"Device ID {device_id} not found.")
    
    await crud_device.update_device_detail(conn, device_id, new_device)
    admin = f"{curr_admin['fname']} {curr_admin['lname']}".title()
    description = f"{admin} updated device '{device['name']}'."
    await Utils.generate_log(conn, description, "admin action", curr_admin['home_id'])

    return {
        "message": f"Successfully updated '{device['name']}'."
    }