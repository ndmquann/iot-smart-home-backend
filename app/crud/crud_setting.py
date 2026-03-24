import asyncpg
from app.schemas.setting import ScheduleCreate, ThresholdCreate

# ==========================================
# SCHEDULE CRUD
# ==========================================
async def create_schedule(conn: asyncpg.Connection, schedule: ScheduleCreate) -> dict:
    async with conn.transaction():
        # 1. insert into base settings table
        query_base = """
            INSERT INTO settings (name)
            VALUES $1
            RETURNING sid;
        """
        new_setting = await conn.fetchrow(query_base, schedule.name)
        sid = new_setting['sid']

        # 2. insert into schedules table
        query_schedule = """
            INSERT INTO schedules (sid, date_start, date_end, time_start, timer)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING sid, date_start, date_end, time_start, timer;
        """
        schedule_data = await conn.fetchrow(
            query_schedule,
            sid,
            schedule.date_start,
            schedule.date_end,
            schedule.time_start,
            schedule.timer
        )

        # merge
        result = {**dict(new_setting), **dict(schedule_data)}
        result['type'] = "schedule"
        return result
    
async def get_all_schedules(conn: asyncpg.Connection) -> list[dict]:
    """
    list of existing schedules
    """
    query = """
        SELECT set.sid, set.type, set.name, sch.date_start, sch.date_end, sch.time_start, sch.timer
        FROM settings set
        JOIN schedules sch ON set.sid = sch.sid   
    """
    records = await conn.fetch(query)
    return [dict(record) for record in records]

# ==========================================
# THRESHOLD CRUD
# ==========================================
async def create_threshold(conn: asyncpg.Connection, threshold: ThresholdCreate) -> dict:
    async with conn.transaction():
        # 1. insert into base settings table
        query_base = """
            INSERT INTO settings (name) 
            VALUES $1
            RETURNING sid;
        """
        new_setting = await conn.fetchrow(query_base, threshold.name)
        sid = new_setting['sid']

        # 2. insert into thresholds table
        query_threshold = """
            INSERT INTO thresholds (sid, value, condition)
            VALUES ($1, $2, $3, $4)
            RETURNING value, condition;
        """
        threshold_data = await conn.fetchrow(
            query_threshold,
            sid,
            threshold.value,
            threshold.condition
        )

        # merge
        result = {**dict(new_setting), **dict(threshold_data)}
        result['type'] = "threshold"
        return result
    
async def get_all_thresholds(conn: asyncpg.Connection) -> list[dict]:
    """
    list of existing thresholds
    """
    query = """
        SELECT set.sid, set.type, set.name, thr.value, thr.condition
        FROM settings set
        JOIN thresholds thr ON set.sid = thr.sid   
    """
    records = await conn.fetch(query)
    return [dict(record) for record in records]

async def delete_setting(conn: asyncpg.Connection, setting_id: int) -> str | None:
    query = """
        SELECT name
        FROM settings
        WHERE sid = $1;
    """
    setting_name = await conn.fetchval(query, setting_id)
    if setting_name:
        await conn.execute("DELETE FROM settings WHERE sid = $1;", setting_id)
    return setting_name

# ==========================================
# HELPER APPLY SETTINGS TO DEVICES
# ==========================================
async def apply_schedule_to_controller(conn: asyncpg.Connection, schedule_id: int, controller_id: int) -> None:
    """
    link a schedule to a specific controller
    """
    query = """
        INSERT INTO schedule_apply (schedule_id, controller_id)
        VALUES ($1, $2);
    """
    await conn.execute(query, schedule_id, controller_id)

async def apply_threshold_to_sensor(conn: asyncpg.Connection, threshold_id: int, sensor_id: int) -> None:
    """
    link a threshold to a specific sensor
    """
    query = """
        INSERT INTO threshold_apply (threshold_id, sensor_id)
        VALUES ($1, $2);
    """
    await conn.execute(query, threshold_id, sensor_id)