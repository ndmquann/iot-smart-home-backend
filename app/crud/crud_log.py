import asyncpg
from app.schemas.log import LogBase

# ==========================================
# 1. INTERACT (User -> Device -> Log)
# ==========================================
async def log_user_action(
        conn: asyncpg.Connection, 
        user_id: int, 
        device_id: int, 
        home_id: str,
        description: str) -> dict:
    """
    logs when a user interacts with a controller
    """
    async with conn.transaction():
        # 1. create log
        query_log = """
            INSERT INTO logs (type, description, home_id)
            VALUES ('user action', $1, $2)
            RETURNING id, type, description, timestamp;
        """
        new_log = await conn.fetchrow(query_log, description, home_id)

        # 2. create mapping
        query_interact = """
            INSERT INTO interact (user_id, device_id, log_id)
            VALUES ($1, $2, $3);
        """
        await conn.execute(query_interact, 
                           user_id, 
                           device_id, 
                           new_log['id'])

        return dict(new_log)
    
# ==========================================
# 2. CONFIG (Admin -> Setting -> Log)
# ==========================================
async def log_admin_action(
        conn: asyncpg.Connection, 
        admin_id: int, 
        setting_id: int, 
        home_id: str, 
        description: str) -> dict:
    """
    logs when an admin configures a setting (schedule or threshold only)
    """
    async with conn.transaction():
        # 1. create log
        query_log = """
            INSERT INTO logs (type, description, home_id)
            VALUES ('admin action', $1, $2)
            RETURNING id, type, description, timestamp;
        """
        new_log = await conn.fetchrow(query_log, description, home_id)

        # 2. create mapping
        query_config = """
            INSERT INTO config (admin_id, setting_id, log_id)
            VALUES ($1, $2, $3);
        """
        await conn.execute(query_config, 
                           admin_id, 
                           setting_id, 
                           new_log['id'])

        return dict(new_log)
    
# ==========================================
# 3. CONTAIN (Setting -> Device -> Log)
# ==========================================
async def log_system_trigger(
        conn: asyncpg.Connection, 
        setting_id: int, 
        device_id: int, 
        home_id: str, 
        description: str, 
        log_type: str="system action") -> dict:
    """
    logs when a schedule triggers a controller
    or a threshold triggers a sensor
    """
    async with conn.transaction():
        # 1. create log
        query_log = """
            INSERT INTO logs (type, description, home_id)
            VALUES ($1, $2, $3)
            RETURNING id, type, description, timestamp;
        """
        new_log = await conn.fetchrow(query_log, description, log_type, home_id)

        # 2. create mapping
        query_contain = """
            INSERT INTO contain (device_id, setting_id, log_id)
            VALUES ($1, $2, $3);
        """
        await conn.execute(query_contain, 
                           device_id, 
                           setting_id, 
                           new_log['id'])

        return dict(new_log)
    
# ==========================================
# FETCHING LOGS (For Module 4 UI)
# ==========================================
async def get_recent_logs(
        conn: asyncpg.Connection, 
        home_id: str,
        limit: int = 50) -> list[dict]:
    """
    fetch latest logs, dynamically pull in the associated
    User, Device, or Setting
    """
    query = """
        SELECT l.id, l.type, l.description, l.timestamp,
            u.fname || ' ' || u.lname AS user_name,
            d.name AS device_name,
            COALESCE(sch.name, thr.name) AS setting_name
        FROM logs l
        -- join interact to get user and controller
        LEFT JOIN interact i ON l.id = i.log_id
        LEFT JOIN users u ON i.user_id = u.id
        LEFT JOIN devices d_interact ON i.controller_id = d_interact.did
        
        -- join config to get admin and setting
        LEFT JOIN config c ON l.id = c.log_id

        -- join contain to get device and setting
        LEFT JOIN contain ct ON l.id = ct.log_id
        LEFT JOIN devices d_contain ON ct.device_id = d_contain.did

        -- consolidate device/setting names from different mapping
        LEFT JOIN devices d ON d.did = COALESCE(d_interact.did, d_contain.did)
        LEFT JOIN schedules sch ON sch.sid = COALESCE(c.setting_id, ct.setting_id)
        LEFT JOIN thresholds thr ON thr.sid = COALESCE(c.setting_id, ct.setting_id)

        WHERE l.home_id = $1
        ORDER BY l.timestamp DESC
        LIMIT $2;
    """
    records = await conn.fetch(query,home_id, limit)
    return [dict(record) for record in records]

async def log_admin_delete_action(
        conn: asyncpg.Connection, 
        admin_name: str, 
        description: str) -> dict:
    full_description = f"{admin_name} {description}"

    query = """
        INSERT INTO logs (type, description)
        VALUES ('admin action', $1)
        RETURNING id, type, description, timestamp;
    """
    new_log = await conn.fetchrow(query, full_description)
    return dict(new_log)