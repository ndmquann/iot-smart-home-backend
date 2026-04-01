import asyncpg
from app.schemas.setting import ScheduleCreate, ThresholdCreate

# ==========================================
# SCHEDULE CRUD
# ==========================================
async def create_schedule(
    conn: asyncpg.Connection, 
    schedule: ScheduleCreate,
    admin_id: int
) -> dict:
    async with conn.transaction():
        # 1. insert into base settings table
        query_base = """
            INSERT INTO settings (name, admin_id)
            VALUES ($1, $2)
            RETURNING id, name, admin_id;
        """
        new_setting = await conn.fetchrow(query_base, schedule.name, admin_id)
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
    list of existing schedules of a home (admin and member can view schedules)
    """
    query_admin = """
        SELECT user_id
        FROM home_group_view
        WHERE home_id = $1 and user_type = 'admin';
    """
    admin_id = await conn.fetchval(query_admin, home_id)

    query = """
        SELECT 
            set.id AS setting_id, 
            set.admin_id,
            'schedule' AS type,
            set.name, 
            sch.date_start, 
            sch.date_end, 
            sch.time_start, 
            sch.timer
        FROM settings set
        JOIN schedules sch ON set.id = sch.setting_id
        WHERE set.admin_id = $1;
    """
    records = await conn.fetch(query, admin_id)
    return [dict(record) for record in records]

# ==========================================
# THRESHOLD CRUD
# ==========================================
async def create_threshold(
    conn: asyncpg.Connection,
    threshold: ThresholdCreate,
    admin_id: int
) -> dict:
    async with conn.transaction():
        # 1. insert into base settings table
        query_base = """
            INSERT INTO settings (name, admin_id) 
            VALUES ($1, $2)
            RETURNING id, name, admin_id;
        """
        new_setting = await conn.fetchrow(query_base, threshold.name, admin_id)
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
    list of existing thresholds
    """
    query_admin = """
        SELECT user_id
        FROM home_group_view
        WHERE home_id = $1 and user_type = 'admin';
    """
    admin_id = await conn.fetchval(query_admin, home_id)
    query = """
        SELECT 
            set.id AS setting_id, 
            set.admin_id, 
            'threshold' AS type,
            set.name, 
            thr.value, 
            thr.condition
        FROM settings set
        JOIN thresholds thr ON set.id = thr.setting_id
        WHERE set.admin_id = $1
    """
    records = await conn.fetch(query, admin_id)
    return [dict(record) for record in records]

async def delete_setting(conn: asyncpg.Connection, setting_id: int) -> str | None:
    query = """
        SELECT name
        FROM settings
        WHERE setting_id = $1;
    """
    setting_name = await conn.fetchval(query, setting_id)
    if setting_name:
        await conn.execute("DELETE FROM settings WHERE setting_id = $1;", setting_id)
    return setting_name

# ==========================================
# HELPER APPLY SETTINGS TO DEVICES
# ==========================================
async def apply_setting_to_device(
    conn: asyncpg.Connection, 
    device_id: int, 
    setting_id: int
):
    query = """
        INSERT INTO apply (device_id, setting_id)
        VALUES ($1, $2);
        ON CONFLICT DO NOTHING;
    """
    await conn.execute(query, device_id, setting_id)