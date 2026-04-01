import asyncpg
from app.schemas.device import DeviceCreate
from typing import List

# ==========================================
# CRUD
# ==========================================

async def create_device(conn: asyncpg.Connection, device: DeviceCreate, admin_id: int) -> dict:
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

async def get_all_devices(conn: asyncpg.Connection) -> list[dict]:
    """
    list of devices order by zone_id and name
    """
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
        ORDER BY d.zone_id, d.name;
    """
    records = await conn.fetch(query)
    return [dict(record) for record in records]

async def update_device_status(conn: asyncpg.Connection, feed_id: str, status: str) -> None:
    """
    when Adafruit IO sends an update,
    update device's status in DB"""
    async with conn.transaction():
        query = """
            UPDATE devices
            SET status = $1
            WHERE feed_id = $2
        """
        await conn.execute(query, status, feed_id)

async def update_sensor_value(conn: asyncpg.Connection, feed_id: str, value: float) -> None:
    """
    when Adafruit IO sends a sensor reading,
    update sensor's value in DB
    """
    async with conn.transaction():
        query = """
            UPDATE sensors
            SET value = $1
            FROM devices d
            WHERE device_id = d.id AND d.feed_id = $2
        """
        await conn.execute(query, value, feed_id)

async def get_device_by_feed_id(conn: asyncpg.Connection, feed_id: str) -> dict | None:
    """
    look up a device by feed id to determine its type
    """
    query = """
        SELECT
            d.id,
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
    query = """
        SELECT *
        FROM devices
        WHERE id = $1
    """
    record = await conn.fetchrow(query, device_id)
    return dict(record) if record else None

async def update_controller_mode(conn: asyncpg.Connection, device_id: int, mode: str):
    query = """
        UPDATE controllers
        SET mode = $1
        WHERE device_id = $2
    """
    await conn.execute(query, mode, device_id)

async def update_controller_speed(conn: asyncpg.Connection, device_id: int, speed: int):
    query = """
        UPDATE controllers
        SET speed = $1
        WHERE device_id = $2
    """
    await conn.execute(query, speed, device_id)

async def delete_device(conn: asyncpg.Connection, device_id: int) -> str | None:
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