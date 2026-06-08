import datetime

import asyncpg
from app.schemas.setting import ScheduleCreate, ThresholdCreate
from app.utils import Utils

# ==========================================
# SCHEDULE CRUD
# ==========================================
async def create_schedule(
    conn: asyncpg.Connection, 
    schedule: ScheduleCreate,
    admin_id: int
) -> dict:
    """
    Create a new schedule setting in the database.
    
    Inserts schedule into base settings table and schedules table. Schedules define
    automated device actions at specific times with optional duration (timer).
    
    Args:
        conn: Async database connection
        schedule: ScheduleCreate schema with name, action, date range, time, timer
        admin_id: ID of the admin creating the schedule
        
    Returns:
        dict: New schedule object with setting details and type='schedule'
    """
    async with conn.transaction():
        # 1. insert into base settings table
        query_base = """
            INSERT INTO settings (name, admin_id, action)
            VALUES ($1, $2, $3)
            RETURNING id, name, admin_id, action;
        """
        new_setting = await conn.fetchrow(query_base, schedule.name, admin_id, schedule.action)
        setting_id = new_setting['id']

        # 2. insert into schedules table
        query_schedule = """
            INSERT INTO schedules (setting_id, date_start, date_end, time_start, timer)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING setting_id, date_start, date_end, time_start, timer;
        """
        schedule_data = await conn.fetchrow(
            query_schedule,
            setting_id,
            schedule.date_start,
            schedule.date_end,
            schedule.time_start,
            schedule.timer
        )

        # merge
        result = {**dict(new_setting), **dict(schedule_data)}
        result['type'] = "schedule"
        return result
    
async def get_all_schedules(conn: asyncpg.Connection, home_id: int) -> list[dict]:
    """
    Retrieve all schedules for a home.
    
    Fetches all schedules that belong to a home. Both admins and members can view schedules.
    Results include complete schedule details: dates, times, timers, and associated actions.
    
    Args:
        conn: Async database connection
        home_id: ID of the home to retrieve schedules for
        
    Returns:
        list: List of schedule objects with setting and timing information
    """
    admin_id = await Utils.get_admin_of_home(conn, home_id)

    query = """
        SELECT 
            set.id AS setting_id, 
            set.admin_id,
            'schedule' AS type,
            set.name, 
            sch.date_start, 
            sch.date_end, 
            sch.time_start, 
            sch.timer,
            set.action
        FROM settings set
        JOIN schedules sch ON set.id = sch.setting_id
        WHERE set.admin_id = $1;
    """
    records = await conn.fetch(query, admin_id)
    return [dict(record) for record in records]

async def get_schedule_by_id(conn: asyncpg.Connection, setting_id: int) -> dict | None:
    """
    Retrieve a specific schedule by its setting ID.
    
    Fetches schedule details including dates, times, duration, and action.
    
    Args:
        conn: Async database connection
        setting_id: ID of the schedule setting to retrieve
        
    Returns:
        dict: Schedule object if found, None otherwise
    """
    query = """
        SELECT 
            set.id AS setting_id, 
            set.admin_id,
            'schedule' AS type,
            set.name, 
            sch.date_start, 
            sch.date_end, 
            sch.time_start, 
            sch.timer,
            set.action
        FROM settings set
        JOIN schedules sch ON set.id = sch.setting_id
        WHERE set.id = $1;
    """
    record = await conn.fetchrow(query, setting_id)
    return dict(record) if record else None

async def update_schedule(
    conn: asyncpg.Connection,
    setting_id: int,
    new_name: str,
    new_schedule: ScheduleCreate,
    admin_id: int
):
    """
    Update an existing schedule setting.
    
    Modifies schedule details including name, date range, time, timer, and action.
    
    Args:
        conn: Async database connection
        setting_id: ID of the schedule to update
        new_name: New schedule name
        new_schedule: ScheduleCreate schema with updated values
        admin_id: Admin ID for authorization
    """
    async with conn.transaction():
        # 1. update base settings table
        query_base = """
            UPDATE settings
            SET name = $1, action = $2
            WHERE id = $3 AND admin_id = $4
            RETURNING id, name, admin_id;
        """
        await conn.fetchrow(query_base, new_name, new_schedule.action, setting_id, admin_id)

        # 2. update schedules table
        query_schedule = """
            UPDATE schedules
            SET date_start = $1, date_end = $2, time_start = $3, timer = $4
            WHERE setting_id = $5
            RETURNING setting_id, date_start, date_end, time_start, timer;
        """
        await conn.fetchrow(
            query_schedule,
            new_schedule.date_start,
            new_schedule.date_end,
            new_schedule.time_start,
            new_schedule.timer,
            setting_id
        )
    
# ==========================================
# THRESHOLD CRUD
# ==========================================
async def create_threshold(
    conn: asyncpg.Connection,
    threshold: ThresholdCreate,
    admin_id: int
) -> dict:
    """
    Create a new threshold setting in the database.
    
    Inserts threshold into base settings table and thresholds table. Thresholds
    define automated actions when sensor values reach/cross specified limits.
    
    Args:
        conn: Async database connection
        threshold: ThresholdCreate schema with name, value, condition, action
        admin_id: ID of the admin creating the threshold
        
    Returns:
        dict: New threshold object with setting details and type='threshold'
    """
    async with conn.transaction():
        # 1. insert into base settings table
        query_base = """
            INSERT INTO settings (name, admin_id, action) 
            VALUES ($1, $2, $3)
            RETURNING id, name, admin_id, action;
        """
        new_setting = await conn.fetchrow(query_base, threshold.name, admin_id, threshold.action)
        setting_id = new_setting['id']

        # 2. insert into thresholds table
        query_threshold = """
            INSERT INTO thresholds (setting_id, value, condition)
            VALUES ($1, $2, $3)
            RETURNING setting_id, value, condition;
        """
        threshold_data = await conn.fetchrow(
            query_threshold,
            setting_id,
            threshold.value,
            threshold.condition
        )

        # merge
        result = {**dict(new_setting), **dict(threshold_data)}
        result['type'] = "threshold"
        return result
    
async def get_all_thresholds(conn: asyncpg.Connection, home_id: int) -> list[dict]:
    """
    Retrieve all thresholds for a home.
    
    Fetches all thresholds that belong to a home. Thresholds define automated actions
    when sensor values reach/cross specified limits. Results include condition, value,
    target device, and associated action.
    
    Args:
        conn: Async database connection
        home_id: ID of the home to retrieve thresholds for
        
    Returns:
        list: List of threshold objects with condition, value, and target device information
    """
    admin_id = await Utils.get_admin_of_home(conn, home_id)
    
    query = """
        SELECT 
            set.id AS setting_id, 
            set.admin_id, 
            'threshold' AS type,
            set.name, 
            thr.value, 
            thr.condition,
            set.action
        FROM settings set
        JOIN thresholds thr ON set.id = thr.setting_id
        WHERE set.admin_id = $1
    """
    records = await conn.fetch(query, admin_id)
    return [dict(record) for record in records]

async def get_threshold_by_id(conn: asyncpg.Connection, setting_id: int) -> dict | None:
    """
    Retrieve a specific threshold by its setting ID.
    
    Fetches threshold details including condition, value, and target device.
    
    Args:
        conn: Async database connection
        setting_id: ID of the threshold setting to retrieve
        
    Returns:
        dict: Threshold object if found, None otherwise
    """
    query = """
        SELECT 
            set.id AS setting_id, 
            set.admin_id, 
            'threshold' AS type,
            set.name, 
            thr.value, 
            thr.condition,
            set.action
        FROM settings set
        JOIN thresholds thr ON set.id = thr.setting_id
        WHERE set.id = $1
    """
    record = await conn.fetchrow(query, setting_id)
    return dict(record) if record else None

async def update_threshold(
    conn: asyncpg.Connection,
    setting_id: int,
    new_name: str,
    new_threshold: ThresholdCreate,
    admin_id: int
):
    """
    Update an existing threshold setting.
    
    Modifies threshold details including name, condition, value, target device, and action.
    
    Args:
        conn: Async database connection
        setting_id: ID of the threshold to update
        new_name: New threshold name
        new_threshold: ThresholdCreate schema with updated values
        admin_id: Admin ID for authorization
    """
    async with conn.transaction():
        # 1. update base settings table
        query_base = """
            UPDATE settings
            SET name = $1, action = $2
            WHERE id = $3 AND admin_id = $4
            RETURNING id, name, admin_id;
        """
        await conn.fetchrow(query_base, new_name, new_threshold.action, setting_id, admin_id)

        # 2. update thresholds table
        query_threshold = """    
            UPDATE thresholds
            SET value = $1, condition = $2
            WHERE setting_id = $3
            RETURNING setting_id, value, condition;
        """
        await conn.fetchrow(
            query_threshold,
            new_threshold.value,
            new_threshold.condition,
            setting_id
        )
    
async def delete_setting(conn: asyncpg.Connection, setting_id: int) -> str | None:
    """
    Delete a schedule or threshold setting from the database.
    
    Permanently removes a setting record. Associated device applications are also deleted.
    
    Args:
        conn: Async database connection
        setting_id: ID of the setting to delete
        
    Returns:
        str: Name of the deleted setting if found, None otherwise
    """
    query = """
        SELECT name
        FROM settings
        WHERE id = $1;
    """
    setting_name = await conn.fetchval(query, setting_id)
    if setting_name:
        await conn.execute("DELETE FROM settings WHERE id = $1;", setting_id)
    return setting_name

# ==========================================
# HELPER APPLY SETTINGS TO DEVICES
# ==========================================
async def apply_setting_to_device(
    conn: asyncpg.Connection, 
    device_id: int, 
    setting_id: int,
    target_device_id: int,
    admin_id: int
):
    """
    Link a schedule or threshold setting to a device with business rule validation.
    
    Associates a setting with a device, enforcing these rules:
    - Thresholds can ONLY be applied to sensors
    - Schedules can ONLY be applied to controllers
    - Both must belong to the same home (enforced by admin_id)
    
    Args:
        conn: Async database connection
        device_id: ID of the device to apply setting to
        setting_id: ID of the schedule or threshold to apply
        target_device_id: ID of the target device
        admin_id: ID of the admin applying the setting
        
    Returns:
        dict: Device type, device name, setting type, setting name for logging
        
    Raises:
        ValueError: If device type doesn't match setting type or if not found
    """
    device_query = """
        SELECT 
            d.name,
            d.admin_id,
            CASE
                WHEN c.device_id IS NOT NULL THEN 'controller'
                WHEN s.device_id IS NOT NULL THEN 'sensor'
            END AS type
        FROM devices d
        LEFT JOIN controllers c ON d.id = c.device_id
        LEFT JOIN sensors s ON d.id = s.device_id
        WHERE d.id = $1;
    """
    device = await conn.fetchrow(device_query, device_id)
    if not device:
        raise ValueError(f"Device ID {device_id} not found or is invalid.")
    if device['admin_id'] != admin_id:
        raise ValueError(f"Device ID {device_id} does not belong to your home.")
    device_type = device['type']

    # 2. Determine the Setting Type
    setting_query = """
        SELECT
            set.name,
            set.admin_id,
            CASE
                WHEN sch.setting_id IS NOT NULL THEN 'schedule'
                WHEN thr.setting_id IS NOT NULL THEN 'threshold'
            END AS type
        FROM settings set
        LEFT JOIN schedules sch ON set.id = sch.setting_id
        LEFT JOIN thresholds thr ON set.id = thr.setting_id
        WHERE set.id = $1;
    """
    setting = await conn.fetchrow(setting_query, setting_id)
    if not setting:
        raise ValueError(f"Setting ID {setting_id} not found or is invalid.")
    if setting['admin_id'] != admin_id:
        raise ValueError(f"Setting ID {setting_id} does not belong to your home.")
    setting_type = setting['type']
    
    # 3. ENFORCE THE BUSINESS LOGIC
    if device_type == 'sensor' and setting_type != 'threshold':
        raise ValueError("Strict Rule: Sensors can only be applied with thresholds.")
    if device_type == 'controller' and setting_type != 'schedule':
        raise ValueError("Strict Rule: Controllers can only be applied with schedules.")

    # 4. Insert into the Apply table
    insert_query = """
        INSERT INTO apply (device_id, setting_id, target_device)
        VALUES ($1, $2, $3)
        ON CONFLICT DO NOTHING; -- Prevents errors if already applied
    """
    await conn.execute(insert_query, device_id, setting_id, target_device_id)
    
    # Return types so the router can use them for logging
    return {"device_type": device_type, 
            "device_name": device['name'], 
            "setting_type": setting_type, 
            "setting_name": setting['name'],
            "target_device_id": target_device_id,
            }

# ==========================================
# SCHEDULER HELPER
# ==========================================
async def get_due_start_schedules(conn: asyncpg.Connection, current_time: datetime, home_id:int) -> list[dict]:
    """
    Fetch schedules that should start executing at the current time.
    
    Retrieves schedules whose start time matches the current time and are within
    their date range. Used by scheduler service to trigger device actions.
    
    Args:
        conn: Async database connection
        current_time: Current datetime to match against schedule time_start
        home_id: ID of the home to filter schedules
        
    Returns:
        list: List of applicable schedules with device and action details
    """
    query = """
        SELECT
            a.device_id,
            d.name AS device_name,
            d.feed_id,
            set.name AS setting_name,
            set.action
        FROM apply a
        JOIN schedules sch ON a.setting_id = sch.setting_id
        JOIN devices d ON a.device_id = d.id
        JOIN settings set ON sch.setting_id = set.id
        JOIN users u ON set.admin_id = u.id
        WHERE
            $1 >= sch.date_start
            AND (sch.date_end IS NULL OR $1 <= sch.date_end)
            AND $2 = EXTRACT(HOUR FROM sch.time_start)
            AND $3 = EXTRACT(MINUTE FROM sch.time_start)
            AND d.status != set.action
            AND u.home_id = $4;
    """
    records = await conn.fetch(
        query, 
        current_time.date(),
        current_time.hour,
        current_time.minute,
        home_id
        )
    return [dict(record) for record in records]

async def get_due_end_schedules(conn: asyncpg.Connection, current_time: datetime, home_id:int) -> list[dict]:
    """
    Fetch schedules that should stop executing at the current time.
    
    Retrieves schedules that have a timer (duration) and whose end time
    (start time + timer) matches the current time. Used by scheduler to turn off devices.
    
    Args:
        conn: Async database connection
        current_time: Current datetime to calculate schedule end times
        home_id: ID of the home to filter schedules

    Returns:
        list: List of applicable schedules with device details for turning off
    """
    query = """
        SELECT
            a.device_id,
            d.name AS device_name,
            d.feed_id,
            set.name AS setting_name,
            set.action
        FROM apply a
        JOIN schedules sch ON a.setting_id = sch.setting_id
        JOIN devices d ON a.device_id = d.id
        JOIN settings set ON sch.setting_id = set.id
        JOIN users u ON set.admin_id = u.id
        WHERE
            $1 >= sch.date_start 
            AND (sch.date_end IS NULL OR $1 <= sch.date_end)
            AND sch.timer IS NOT NULL
            AND sch.timer > 0
            AND $2 = EXTRACT(HOUR FROM (sch.time_start + (sch.timer * interval '1 minute')))
            AND $3 = EXTRACT(MINUTE FROM (sch.time_start + (sch.timer * interval '1 minute')))
            AND d.status != CASE 
                WHEN set.action = 'ON' THEN 'OFF'
                ELSE 'ON'
            END
            AND u.home_id = $4;
    """
    records = await conn.fetch(
        query, 
        current_time.date(),
        current_time.hour,
        current_time.minute,
        home_id
        )
    return [dict(record) for record in records]

async def get_triggered_thresholds(conn: asyncpg.Connection, home_id: int) -> list[dict]:
    """
    Fetch thresholds whose conditions have been met by current sensor values.
    
    Retrieves thresholds where sensor readings satisfy the threshold condition
    (value >= limit for 'true' or value <= limit for 'false'). Used by threshold
    engine to trigger automated device actions.
    
    Args:
        conn: Async database connection
        home_id: ID of the home to filter thresholds
        
    Returns:
        list: List of triggered thresholds with sensor, target device, and action details
    """
    query = """
        SELECT
            a.target_device AS target_device_id,
            t_ctrl.name AS target_device_name,
            t_ctrl.feed_id AS target_feed_id,
            set.action,
            u.home_id,
            s_sensor.name AS sensor_name,
            s.value AS current_sensor_value,
            thr.value AS threshold_limit
        FROM apply a
        JOIN thresholds thr ON a.setting_id = thr.setting_id
        JOIN settings set ON thr.setting_id = set.id
        JOIN users u ON set.admin_id = u.id
        JOIN devices s_sensor ON a.device_id = s_sensor.id -- The Sensor reading the data
        JOIN sensors s ON s_sensor.id = s.device_id
        JOIN devices t_ctrl ON a.target_device = t_ctrl.id -- The Target Controller to turn ON/OFF
        WHERE
            (
                (thr.condition = 'true' AND s.value >= thr.value) -- Greater than or equal
                OR 
                (thr.condition = 'false' AND s.value <= thr.value) -- Lower than or equal
            )
            AND t_ctrl.status != set.action
            AND u.home_id = $1;
    """
    records = await conn.fetch(query, home_id)
    return [dict(record) for record in records]