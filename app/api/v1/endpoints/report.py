from datetime import date, timedelta

import asyncpg
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.db.database import get_db_connection
from app.api.dependencies import get_current_admin
from app.crud import crud_report
from app.schemas.report import ReportSummary
from app.services import report_gen
from app.core.exceptions import BadRequestException, DatabaseException

router = APIRouter()


# ==========================================
# SHARED HELPERS
# ==========================================

def _resolve_date_range(days: int) -> tuple[date, date]:
    """Return (date_from, date_to) for the last `days` days ending today."""
    date_to   = date.today()
    date_from = date_to - timedelta(days=days - 1)
    return date_from, date_to


def _validate_days(days: int) -> None:
    if days < 1 or days > 60:
        raise BadRequestException("days must be between 1 and 60.")


# ==========================================
# ENDPOINTS
# ==========================================

@router.get(
    "/summary",
    response_model=ReportSummary,
    summary="JSON report — full home summary",
)
async def get_report_summary(
    days: int = Query(7, ge=1, le=60, description="Reporting window: 1–60 days (default 7)"),
    curr_admin: dict = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """
    Return a complete JSON report covering zones, devices, automations,
    and activity for the admin's home within the chosen time window.

    Only the requesting admin's home data is included.

    Args:
        days:       Number of past days to include (1–60, default 7)
        curr_admin: Authenticated admin (enforced by dependency)
        conn:       Async DB connection

    Returns:
        ReportSummary: Full structured report ready for frontend consumption

    Raises:
        BadRequestException: If `days` is out of range (guard kept for explicit messaging)
        DatabaseException:   On unexpected DB error
    """
    _validate_days(days)
    date_from, date_to = _resolve_date_range(days)

    try:
        report = await crud_report.build_report(
            conn=conn,
            admin_id=curr_admin['id'],
            home_id=curr_admin['home_id'],
            date_from=date_from,
            date_to=date_to,
            days=days,
        )
        return report
    except Exception as e:
        raise DatabaseException(f"Failed to build report: {str(e)}")


@router.get(
    "/pdf",
    summary="PDF report — downloadable file with charts",
    response_class=StreamingResponse,
)
async def get_report_pdf(
    days: int = Query(7, ge=1, le=60, description="Reporting window: 1–60 days (default 7)"),
    curr_admin: dict = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """
    Generate and stream a PDF report for the admin's home.

    The PDF contains:
    - KPI summary strip (floors, rooms, devices, automations, log count)
    - Zone table per floor
    - Device table with status/type pie charts
    - Automation table with period trigger counts
    - Activity breakdown table and bar chart

    Only the requesting admin's home data is included.

    Args:
        days:       Number of past days to include (1–60, default 7)
        curr_admin: Authenticated admin
        conn:       Async DB connection

    Returns:
        StreamingResponse: application/pdf binary stream with Content-Disposition header

    Raises:
        DatabaseException: On DB or PDF generation error
    """
    _validate_days(days)
    date_from, date_to = _resolve_date_range(days)

    try:
        report = await crud_report.build_report(
            conn=conn,
            admin_id=curr_admin['id'],
            home_id=curr_admin['home_id'],
            date_from=date_from,
            date_to=date_to,
            days=days,
        )
        pdf_buffer = report_gen.generate_pdf(report)

        filename = f"smart_home_report_{date_from}_to_{date_to}.pdf"
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise DatabaseException(f"Failed to generate PDF report: {str(e)}")


@router.get(
    "/csv/sensors",
    summary="CSV export — sensor history time-series",
    response_class=StreamingResponse,
)
async def get_csv_sensors(
    days: int = Query(7, ge=1, le=60, description="Reporting window: 1–60 days (default 7)"),
    curr_admin: dict = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """
    Export sensor history readings as CSV for the admin's home.

    Columns: device_name, floor, room, value, timestamp

    Only sensors owned by the requesting admin are included.

    Args:
        days:       Number of past days to include (1–60, default 7)
        curr_admin: Authenticated admin
        conn:       Async DB connection

    Returns:
        StreamingResponse: text/csv stream with Content-Disposition header

    Raises:
        DatabaseException: On unexpected DB error
    """
    _validate_days(days)
    date_from, date_to = _resolve_date_range(days)

    try:
        records = await crud_report.get_sensor_history_rows(
            conn=conn,
            admin_id=curr_admin['id'],
            date_from=date_from,
            date_to=date_to,
        )
        csv_buffer = report_gen.generate_csv_sensors(records)

        filename = f"sensor_history_{date_from}_to_{date_to}.csv"
        return StreamingResponse(
            csv_buffer,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'}
        )
    except Exception as e:
        raise DatabaseException(f"Failed to export sensor CSV: {str(e)}")


@router.get(
    "/csv/logs",
    summary="CSV export — activity log entries",
    response_class=StreamingResponse,
)
async def get_csv_logs(
    days: int = Query(7, ge=1, le=60, description="Reporting window: 1–60 days (default 7)"),
    curr_admin: dict = Depends(get_current_admin),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """
    Export activity log entries as CSV for the admin's home.

    Columns: id, type, description, timestamp

    Scoped strictly to the requesting admin's home_id.

    Args:
        days:       Number of past days to include (1–60, default 7)
        curr_admin: Authenticated admin
        conn:       Async DB connection

    Returns:
        StreamingResponse: text/csv stream with Content-Disposition header

    Raises:
        DatabaseException: On unexpected DB error
    """
    _validate_days(days)
    date_from, date_to = _resolve_date_range(days)

    try:
        records = await crud_report.get_log_rows(
            conn=conn,
            home_id=curr_admin['home_id'],
            date_from=date_from,
            date_to=date_to,
        )
        csv_buffer = report_gen.generate_csv_logs(records)

        filename = f"activity_logs_{date_from}_to_{date_to}.csv"
        return StreamingResponse(
            csv_buffer,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        raise DatabaseException(f"Failed to export logs CSV: {str(e)}")