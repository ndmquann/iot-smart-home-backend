import asyncpg
from app.schemas.zone import ZoneCreate

async def create_zone(conn: asyncpg.Connection, zone: ZoneCreate, admin_id: int) -> dict:
    async with conn.transaction():
        query = """
            INSERT INTO zones (admin_id, floor, room)
            VALUES ($1, $2, $3)
            RETURNING id, admin_id, floor, room;
        """
        record = await conn.fetchrow(query, admin_id, zone.floor, zone.room)
        return dict(record)
    
async def get_all_zones(conn: asyncpg.Connection) -> list[dict]:
    """
    list of zones order by floor and room"""
    query = """
        SELECT id, floor, room
        FROM zones
        ORDER BY floor, room;
    """
    records = await conn.fetch(query)
    return [dict(record) for record in records]

async def get_zone_by_floor(conn: asyncpg.Connection, floor: int) -> list[dict] | None:
    """
    list of ordered rooms in a floor
    """
    query = """
        SELECT *
        FROM zones
        WHERE floor = $1
        ORDER BY room;
    """
    records = await conn.fetch(query, floor)
    return [dict(record) for record in records] if records else None

async def delete_zone(conn: asyncpg.Connection, zone_id: int) -> str | None:
    """
    only delete if there are no devices in the zone
    """
    device_check = "SELECT COUNT(*) FROM devices WHERE zone_id = $1;"
    device_count = await conn.fetchval(device_check, zone_id)
    
    if device_count > 0:
        raise ValueError(f"Cannot delete zone. Please reassign or delete {device_count} devices inside first.")
    
    query = """
        SELECT floor, room
        FROM zones
        WHERE id = $1;
    """
    record = await conn.fetchrow(query, zone_id)
    if record:
        await conn.execute("DELETE FROM zones WHERE id = $1;", zone_id)
        return dict(record)
    
    return None

async def delete_floor(conn: asyncpg.Connection, floor: int) -> list[str]:
    """
    only delete if there is no rooms on this floor have devices
    """
    device_check = """
        SELECT COUNT(d.did)
        FROM devices d
        JOIN zones z ON d.zone_id = z.id
        WHERE z.floor = $1;
    """
    device_count = await conn.fetchval(device_check, floor)

    if device_count > 0:
        raise ValueError(f"Cannot delete floor. There are {device_count} device(s) still attached to rooms on this floor.")
    
    query = """SELECT room FROM zones WHERE floor = $1;"""
    rooms = await conn.fetch(query, floor)
    room_names = [room['room'] for room in rooms]

    if room_names:
        await conn.execute("DELETE FROM zones WHERE floor = $1;", floor)
    
    return room_names