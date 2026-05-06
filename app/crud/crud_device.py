import asyncpg
from app.schemas.device import DeviceCreate, DeviceBase
from typing import List
from app.utils import Utils

# ==========================================
# CRUD
# ==========================================

async def create_device(conn: asyncpg.Connection, device: DeviceCreate, admin_id: int) -> dict:
    """
    Create a new device (sensor or controller) in the database.
    
    Inserts device record into devices table and corresponding record into either
    sensors or controllers table based on device type.
    
    Args:
        conn: Async database connection
        device: DeviceCreate schema with name, zone_id, status, feed_id, type
        admin_id: ID of the admin creating the device
        
    Returns:
        dict: New device object with all details including id, name, zone_id, feed_id, status, type
    """
    async with conn.transaction():
        query = """
            INSERT INTO devices (admin_id, zone_id, name, status, feed_id)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, admin_id, zone_id, name, status, feed_id;
        """
        new_device_record = await conn.fetchrow(
            query, 
            admin_id, 
            device.zone_id, 
            device.name, 
            device.status, 
            device.feed_id
        )

        device_id = new_device_record['id']
        if device.type == "controller":
            await conn.execute(
                "INSERT INTO controllers (device_id) VALUES ($1);", device_id
            )
        elif device.type == "sensor":
            await conn.execute(
                "INSERT INTO sensors (device_id) VALUES ($1);", device_id
            )
        
        result = dict(new_device_record)
        result['type'] = device.type
        result['value'] = None
        return result

async def get_all_devices(conn: asyncpg.Connection, home_id: int) -> list[dict]:
    """
    list of devices in a home order by zone_id and name
    """
    admin_id = await Utils.get_admin_of_home(conn, home_id)
    query = """
        SELECT  
            d.id, d.admin_id, d.zone_id, d.name, d.status, d.feed_id,
            s.value,
            CASE 
                WHEN c.device_id IS NOT NULL THEN 'controller'
                WHEN s.device_id IS NOT NULL THEN 'sensor'
            END AS type
        FROM devices d
        LEFT JOIN controllers c ON d.id = c.device_id
        LEFT JOIN sensors s ON d.id = s.device_id
        WHERE d.admin_id = $1
        ORDER BY d.zone_id, d.name;
    """
    records = await conn.fetch(query, admin_id)
    return [dict(record) for record in records]

async def update_device_status(conn: asyncpg.Connection, device_id: int, status: str) -> None:
    """
    when Adafruit IO sends an update,
    update device's status in DB"""
    async with conn.transaction():
        query = """
            UPDATE devices
            SET status = $1
            WHERE id = $2
        """
        await conn.execute(query, status.upper(), device_id)

async def update_sensor_value(conn: asyncpg.Connection, device_id: int, value: float) -> None:
    """
    when Adafruit IO sends a sensor reading,
    update sensor's value in DB
    """
    async with conn.transaction():
        query = """
            UPDATE sensors
            SET value = $1
            FROM devices d
            WHERE device_id = $2
        """
        await conn.execute(query, value, device_id)

async def get_device_by_feed_id(conn: asyncpg.Connection, feed_id: str) -> dict | None:
    """
    Retrieve a device by its feed ID.
    
    Fetches complete device information from the devices table.
    
    Args:
        conn: Async database connection
        feed_id: Feed ID of the device to retrieve
        
    Returns:
        dict: Device object if found, None otherwise

    When to use:
        Device id is not known, but feed id is
    """
    query = """
        SELECT
            d.*,
            CASE
                WHEN s.device_id IS NOT NULL THEN 'sensor'
                WHEN c.device_id IS NOT NULL THEN 'controller'
            END AS type
        FROM devices d
        LEFT JOIN sensors s ON d.id = s.device_id
        LEFT JOIN controllers c ON d.id = c.device_id
        WHERE d.feed_id = $1
    """
    record = await conn.fetchrow(query, feed_id)
    return dict(record) if record else None

async def get_device_by_id(conn: asyncpg.Connection, device_id: int) -> dict | None:
    """
    Retrieve a device by its ID.
    
    Fetches complete device information from the devices table.
    
    Args:
        conn: Async database connection
        device_id: ID of the device to retrieve
        
    Returns:
        dict: Device object if found, None otherwise
    """
    query = """
        SELECT 
            d.*,
            CASE 
                WHEN s.device_id IS NOT NULL THEN 'sensor'
                WHEN c.device_id IS NOT NULL THEN 'controller'
            END AS type
        FROM devices d
        LEFT JOIN controllers c ON d.id = c.device_id
        LEFT JOIN sensors s ON d.id = s.device_id
        WHERE d.id = $1;
    """
    record = await conn.fetchrow(query, device_id)
    return dict(record) if record else None

async def update_controller_mode(conn: asyncpg.Connection, device_id: int, mode: str):
    """
    Update the operational mode of a controller device.
    
    Changes controller mode to 'manual' or 'auto'. Mode determines whether the
    device is controlled manually or by automated rules.
    
    Args:
        conn: Async database connection
        device_id: ID of the controller device
        mode: 'manual' or 'auto'
    """
    query = """
        UPDATE controllers
        SET mode = $1
        WHERE device_id = $2
    """
    await conn.execute(query, mode, device_id)

async def update_controller_speed(conn: asyncpg.Connection, device_id: int, speed: int):
    """
    Update the speed/power level of a controller device.
    
    Sets the speed level (0-100) for devices that support variable speed control.
    
    Args:
        conn: Async database connection
        device_id: ID of the controller device
        speed: Speed value between 0 and 100
    """
    query = """
        UPDATE controllers
        SET speed = $1
        WHERE device_id = $2
    """
    await conn.execute(query, speed, device_id)

async def delete_device(conn: asyncpg.Connection, device_id: int) -> str | None:
    """
    Delete a device from the database.
    
    Permanently removes a device record and associated sensor/controller record.
    
    Args:
        conn: Async database connection
        device_id: ID of the device to delete
        
    Returns:
        str: Name of the deleted device if successful, None if device not found
    """
    query = """
        SELECT name
        FROM devices
        WHERE id = $1;
    """
    device_name = await conn.fetchval(query, device_id)
    if device_name:
        await conn.execute("DELETE FROM devices WHERE id = $1;", device_id)
    return device_name

async def read_device_detail(conn: asyncpg.Connection, device_id: int) -> dict | None:
    """
    Retrieve detailed information about a device.
    
    Fetches comprehensive device data including type-specific fields (sensor value,
    controller mode/speed), zone assignment, feed ID, and current status.
    
    Args:
        conn: Async database connection
        device_id: ID of the device
        
    Returns:
        dict: Device detail object with all fields if found, None otherwise
    """
    query = """
        SELECT 
            d.id,
            d.name,
            d.zone_id AS zone,
            d.feed_id AS feed,
            d.status,
            s.value AS sensor_value,
            c.mode AS controller_mode,
            c.speed AS controller_speed,
            CASE
                WHEN s.device_id IS NOT NULL THEN 'sensor'
                WHEN c.device_id IS NOT NULL THEN 'controller'
                ELSE 'unknown'
            END as type
        FROM devices d
        LEFT JOIN sensors s ON s.device_id = d.id
        LEFT JOIN controllers c ON c.device_id = d.id
        WHERE d.id = $1;
    """
    record = await conn.fetchrow(query, device_id)
    return dict(record) if record else None

async def get_sensor_history(
    conn: asyncpg.Connection,
    device_id: int,
    limit: int = 50
) -> List[dict]:
    """
    fetch time-series data for a sensor
    """
    query = """
        SELECT value, timestamp
        FROM sensor_history
        WHERE device_id = $1
        ORDER BY timestamp DESC
        LIMIT $2;
    """
    records = await conn.fetch(query, device_id, limit)
    return [dict(record) for record in records]

async def update_device_detail(
    conn: asyncpg.Connection,
    device_id: int,
    new_device: DeviceBase
):
    query = """
        UPDATE devices
        SET name = $1, zone_id = $2, feed_id = $3
        WHERE id = $4;
    """
    await conn.execute(query, new_device.name, new_device.zone_id, new_device.feed_id, device_id)