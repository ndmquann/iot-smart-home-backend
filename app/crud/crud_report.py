import asyncpg
from datetime import date, datetime
from collections import defaultdict
from app.schemas.report import (
    ReportSummary, FloorSummary, ZoneDetail,
    DeviceDetail, AutomationDetail, ActivityBreakdown, SensorHistoryData, SensorReadingPoint
)


# ==========================================
# SUB-QUERIES
# ==========================================

async def _get_zone_rows(conn: asyncpg.Connection, admin_id: int) -> list[dict]:
    """All zones with device counts for this admin."""
    query = """
        SELECT
            z.id   AS zone_id,
            z.floor,
            z.room,
            COUNT(d.id) AS device_count
        FROM zones z
        LEFT JOIN devices d ON z.id = d.zone_id
        WHERE z.admin_id = $1
        GROUP BY z.id, z.floor, z.room
        ORDER BY z.floor, z.room;
    """
    records = await conn.fetch(query, admin_id)
    return [dict(r) for r in records]


async def _get_device_rows(conn: asyncpg.Connection, admin_id: int) -> list[dict]:
    """All devices with zone info and current sensor value."""
    query = """
        SELECT
            d.id,
            d.name,
            d.status,
            COALESCE(z.floor, 0)  AS floor,
            COALESCE(z.room, 'Unassigned') AS room,
            s.value AS current_value,
            CASE
                WHEN c.device_id IS NOT NULL THEN 'controller'
                WHEN s.device_id IS NOT NULL THEN 'sensor'
            END AS type
        FROM devices d
        LEFT JOIN zones z         ON d.zone_id   = z.id
        LEFT JOIN controllers c   ON d.id        = c.device_id
        LEFT JOIN sensors s       ON d.id        = s.device_id
        WHERE d.admin_id = $1
        ORDER BY z.floor, z.room, d.name;
    """
    records = await conn.fetch(query, admin_id)
    return [dict(r) for r in records]


async def _get_automation_rows(
    conn: asyncpg.Connection,
    admin_id: int,
    home_id: int,
    date_from: date,
    date_to: date
) -> list[dict]:
    """
    All settings with type, applied device names, and system-action
    trigger count for the reporting period.

    Trigger count is approximated by counting 'system action' log entries
    whose description contains the setting name within the period.
    """
    query = """
        SELECT
            set.id   AS setting_id,
            set.name,
            set.action,
            CASE
                WHEN sch.setting_id IS NOT NULL THEN 'schedule'
                WHEN thr.setting_id IS NOT NULL THEN 'threshold'
            END AS type,
            COALESCE(STRING_AGG(DISTINCT d.name, ', '), '') AS applied_devices,
            (
                SELECT COUNT(*)
                FROM logs l
                WHERE l.home_id   = $4
                  AND l.type      = 'system action'
                  AND l.description LIKE '%' || set.name || '%'
                  AND DATE(l.timestamp) BETWEEN $2 AND $3
            ) AS trigger_count
        FROM settings set
        LEFT JOIN schedules   sch ON set.id = sch.setting_id
        LEFT JOIN thresholds  thr ON set.id = thr.setting_id
        LEFT JOIN apply       a   ON set.id = a.setting_id
        LEFT JOIN devices     d   ON a.device_id = d.id
        WHERE set.admin_id = $1
        GROUP BY set.id, set.name, set.action, sch.setting_id, thr.setting_id
        ORDER BY set.name;
    """
    records = await conn.fetch(query, admin_id, date_from, date_to, home_id)
    return [dict(r) for r in records]


async def _get_activity_breakdown(
    conn: asyncpg.Connection,
    home_id: int,
    date_from: date,
    date_to: date
) -> list[dict]:
    """Log counts grouped by type within the period."""
    query = """
        SELECT type, COUNT(*) AS count
        FROM logs
        WHERE home_id = $1
          AND DATE(timestamp) BETWEEN $2 AND $3
        GROUP BY type
        ORDER BY count DESC;
    """
    records = await conn.fetch(query, home_id, date_from, date_to)
    return [dict(r) for r in records]


async def _get_sensor_history_stats(
    conn: asyncpg.Connection,
    admin_id: int,
    date_from: date,
    date_to: date
) -> list[dict]:
    """
    Sensor reading statistics (min, max, avg, count) grouped by device
    within the period. Only includes sensors owned by this admin.
    """
    query = """
        SELECT
            d.id AS device_id,
            d.name AS device_name,
            COALESCE(z.floor, 0) AS floor,
            COALESCE(z.room, 'Unassigned') AS room,
            MIN(sh.value) AS min_value,
            MAX(sh.value) AS max_value,
            AVG(sh.value) AS avg_value,
            COUNT(sh.value) AS reading_count
        FROM devices d
        LEFT JOIN zones z ON d.zone_id = z.id
        LEFT JOIN sensor_history sh ON d.id = sh.device_id
            AND DATE(sh.timestamp) BETWEEN $2 AND $3
        WHERE d.admin_id = $1
        GROUP BY d.id, d.name, z.floor, z.room
        HAVING COUNT(sh.value) > 0
        ORDER BY z.floor, z.room, d.name;
    """
    records = await conn.fetch(query, admin_id, date_from, date_to)
    return [dict(r) for r in records]


async def _get_sensor_timeseries(
    conn: asyncpg.Connection,
    admin_id: int,
    date_from: date,
    date_to: date
) -> dict:
    """
    Fetch time-series sensor readings grouped by device_id.
    Returns a dict mapping device_id -> list of (timestamp, value) tuples.
    """
    query = """
        SELECT
            d.id AS device_id,
            sh.timestamp,
            sh.value
        FROM sensor_history sh
        JOIN devices d ON sh.device_id = d.id
        WHERE d.admin_id = $1
          AND DATE(sh.timestamp) BETWEEN $2 AND $3
        ORDER BY d.id, sh.timestamp ASC;
    """
    records = await conn.fetch(query, admin_id, date_from, date_to)
    
    timeseries = defaultdict(list)
    for r in records:
        timeseries[r['device_id']].append({
            'timestamp': r['timestamp'],
            'value': r['value']
        })
    return dict(timeseries)


# ==========================================
# CSV RAW DATA QUERIES
# ==========================================

async def get_sensor_history_rows(
    conn: asyncpg.Connection,
    admin_id: int,
    date_from: date,
    date_to: date
) -> list[dict]:
    """
    Time-series sensor readings in the period for CSV export.
    Scoped strictly to devices owned by this admin.
    """
    query = """
        SELECT
            d.name      AS device_name,
            z.floor,
            z.room,
            sh.value,
            sh.timestamp
        FROM sensor_history sh
        JOIN devices d ON sh.device_id = d.id
        JOIN zones   z ON d.zone_id    = z.id
        WHERE d.admin_id = $1
          AND DATE(sh.timestamp) BETWEEN $2 AND $3
        ORDER BY d.name, sh.timestamp DESC;
    """
    records = await conn.fetch(query, admin_id, date_from, date_to)
    return [dict(r) for r in records]


async def get_log_rows(
    conn: asyncpg.Connection,
    home_id: int,
    date_from: date,
    date_to: date
) -> list[dict]:
    """
    All log entries in the period for CSV export.
    Scoped to the admin's home.
    """
    query = """
        SELECT id, type, description, timestamp
        FROM logs
        WHERE home_id = $1
          AND DATE(timestamp) BETWEEN $2 AND $3
        ORDER BY timestamp DESC;
    """
    records = await conn.fetch(query, home_id, date_from, date_to)
    return [dict(r) for r in records]


# ==========================================
# REPORT ASSEMBLY
# ==========================================

async def build_report(
    conn: asyncpg.Connection,
    admin_id: int,
    home_id: int,
    date_from: date,
    date_to: date,
    days: int
) -> ReportSummary:
    """
    Assemble the full home report from all sub-queries.
    All data is strictly scoped to the requesting admin's home.

    Args:
        conn:       Async DB connection
        admin_id:   ID of the requesting admin (owns devices/zones/settings)
        home_id:    Home the admin belongs to (owns logs)
        date_from:  Start of reporting period
        date_to:    End of reporting period
        days:       Number of days in the period (for display)

    Returns:
        ReportSummary Pydantic model ready for JSON serialisation or PDF render
    """
    zone_rows        = await _get_zone_rows(conn, admin_id)
    device_rows      = await _get_device_rows(conn, admin_id)
    automation_rows  = await _get_automation_rows(conn, admin_id, home_id, date_from, date_to)
    activity_rows    = await _get_activity_breakdown(conn, home_id, date_from, date_to)
    sensor_history_rows = await _get_sensor_history_stats(conn, admin_id, date_from, date_to)
    sensor_timeseries = await _get_sensor_timeseries(conn, admin_id, date_from, date_to)

    # ---- Zone section ------------------------------------------------
    floors_map: dict[int, list] = defaultdict(list)
    for z in zone_rows:
        floors_map[z['floor']].append(
            ZoneDetail(
                zone_id=z['zone_id'],
                floor=z['floor'],
                room=z['room'],
                device_count=z['device_count']
            )
        )

    floors = [
        FloorSummary(
            floor=floor_num,
            room_count=len(rooms),
            device_count=sum(r.device_count for r in rooms),
            rooms=rooms
        )
        for floor_num, rooms in sorted(floors_map.items())
    ]

    # ---- Device section ----------------------------------------------
    devices = [
        DeviceDetail(
            id=d['id'],
            name=d['name'],
            type=d['type'] or 'unknown',
            status=d['status'],
            floor=d['floor'],
            room=d['room'],
            current_value=d['current_value']
        )
        for d in device_rows
    ]

    total_sensors     = sum(1 for d in devices if d.type == 'sensor')
    total_controllers = sum(1 for d in devices if d.type == 'controller')
    devices_on        = sum(1 for d in devices if d.status == 'ON')
    devices_off       = sum(1 for d in devices if d.status == 'OFF')

    # ---- Automation section ------------------------------------------
    automations = [
        AutomationDetail(
            setting_id=a['setting_id'],
            name=a['name'],
            type=a['type'] or 'unknown',
            action=a['action'],
            trigger_count=a['trigger_count'],
            applied_devices=a['applied_devices'] or '-'
        )
        for a in automation_rows
    ]

    total_schedules  = sum(1 for a in automations if a.type == 'schedule')
    total_thresholds = sum(1 for a in automations if a.type == 'threshold')

    # ---- Activity section --------------------------------------------
    activity_breakdown = [
        ActivityBreakdown(type=a['type'], count=a['count'])
        for a in activity_rows
    ]
    total_logs = sum(a.count for a in activity_breakdown)

    # ---- Sensor History section ------------------------------------------
    sensor_history = [
        SensorHistoryData(
            device_id=s['device_id'],
            device_name=s['device_name'],
            floor=s['floor'],
            room=s['room'],
            min_value=s['min_value'],
            max_value=s['max_value'],
            avg_value=round(s['avg_value'], 2) if s['avg_value'] else None,
            reading_count=s['reading_count'],
            readings=[
                SensorReadingPoint(timestamp=r['timestamp'], value=r['value'])
                for r in sensor_timeseries.get(s['device_id'], [])
            ]
        )
        for s in sensor_history_rows
    ]

    return ReportSummary(
        home_id=home_id,
        generated_at=datetime.now(),
        date_from=date_from,
        date_to=date_to,
        days=days,
        total_floors=len(floors),
        total_zones=len(zone_rows),
        floors=floors,
        total_devices=len(devices),
        total_sensors=total_sensors,
        total_controllers=total_controllers,
        devices_on=devices_on,
        devices_off=devices_off,
        devices=devices,
        total_schedules=total_schedules,
        total_thresholds=total_thresholds,
        automations=automations,
        total_logs_in_period=total_logs,
        activity_breakdown=activity_breakdown,
        sensor_history=sensor_history,
    )