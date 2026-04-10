import asyncpg
from app.schemas.zone import ZoneCreate
from app.utils import Utils

async def create_zone(conn: asyncpg.Connection, zone: ZoneCreate, admin_id: int) -> dict:
    """
    Create a new zone (room) in the database.
    
    Inserts a new zone record associated with the admin and returns zone details.
    
    Args:
        conn: Async database connection
        zone: ZoneCreate schema with floor and room name
        admin_id: ID of the admin creating the zone
        
    Returns:
        dict: New zone object with id, admin_id, floor, and room
    """
    async with conn.transaction():
        query = """
            INSERT INTO zones (admin_id, floor, room)
            VALUES ($1, $2, $3)
            RETURNING id, admin_id, floor, room;
        """
        record = await conn.fetchrow(query, admin_id, zone.floor, zone.room)
        return dict(record)
    
async def get_all_zones(conn: asyncpg.Connection, home_id: int) -> list[dict]:
    """
    list of zones order by floor and room"""
    admin_id = await Utils.get_admin_of_home(conn, home_id)

    query = """
        SELECT *
        FROM zones
        WHERE admin_id = $1
        ORDER BY floor, room;
    """
    records = await conn.fetch(query, admin_id)
    return [dict(record) for record in records]

async def get_zone_by_floor(conn: asyncpg.Connection, floor: int, home_id: int) -> list[dict] | None:
    """
    Retrieve all rooms on a specific floor for a home.
    
    Fetches all zones (rooms) on a given floor, ordered by room name.
    Requires home_id to ensure admin context validation.
    
    Args:
        conn: Async database connection
        floor: Floor number
        home_id: ID of the home for context
        
    Returns:
        list: List of zone objects ordered by room name, None if no zones found
    """
    admin_id = await Utils.get_admin_of_home(conn, home_id)

    query = """
        SELECT *
        FROM zones
        WHERE floor = $1 AND admin_id = $2
        ORDER BY room;
    """
    records = await conn.fetch(query, floor, admin_id)
    return [dict(record) for record in records] if records else None

async def delete_zone(conn: asyncpg.Connection, zone_id: int) -> str | None:
    """
    Delete a zone (room) from the database.
    
    Permanently removes a zone record. Validation ensures no devices are attached
    to the zone before deletion.
    
    Args:
        conn: Async database connection
        zone_id: ID of the zone to delete
        
    Returns:
        dict: Zone info with floor and room if successful, None if not found
        
    Raises:
        ValueError: If zone still has devices attached
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

async def delete_floor(conn: asyncpg.Connection, floor: int, home_id: int) -> list[str]:
    """
    Delete all rooms on a specific floor.
    
    Permanently removes all zones on a given floor for a home. Validation ensures
    no devices are attached to any rooms on the floor before deletion.
    
    Args:
        conn: Async database connection
        floor: Floor number to delete
        home_id: ID of the home for context
        
    Returns:
        list: List of room names that were deleted
        
    Raises:
        ValueError: If any rooms on floor still have devices attached
    """
    admin_id = await Utils.get_admin_of_home(conn, home_id)

    device_check = """
        SELECT COUNT(d.id)
        FROM devices d
        JOIN zones z ON d.zone_id = z.id
        WHERE z.floor = $1 AND z.admin_id = $2;
    """
    device_count = await conn.fetchval(device_check, floor, admin_id)

    if device_count > 0:
        raise ValueError(f"Cannot delete floor. There are {device_count} device(s) still attached to rooms on this floor.")
    
    query = """SELECT room FROM zones WHERE floor = $1 AND admin_id = $2;"""
    rooms = await conn.fetch(query, floor, admin_id)
    room_names = [room['room'] for room in rooms]

    if room_names:
        await conn.execute("DELETE FROM zones WHERE floor = $1 AND admin_id = $2;", floor, admin_id)
    
    return room_names