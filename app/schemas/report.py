from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


class ZoneDetail(BaseModel):
    zone_id: int
    floor: int
    room: str
    device_count: int


class FloorSummary(BaseModel):
    floor: int
    room_count: int
    device_count: int
    rooms: List[ZoneDetail]


class DeviceDetail(BaseModel):
    id: int
    name: str
    type: str
    status: str
    floor: int
    room: str
    current_value: Optional[float] = None


class AutomationDetail(BaseModel):
    setting_id: int
    name: str
    type: str           # 'schedule' or 'threshold'
    action: str
    trigger_count: int  # system action logs matching this setting name in the period
    applied_devices: str  # comma-separated device names


class ActivityBreakdown(BaseModel):
    type: str
    count: int


class SensorReadingPoint(BaseModel):
    timestamp: datetime
    value: float


class SensorHistoryData(BaseModel):
    device_id: int
    device_name: str
    floor: int
    room: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    avg_value: Optional[float] = None
    reading_count: int = 0
    readings: List[SensorReadingPoint] = []


class ReportSummary(BaseModel):
    home_id: int
    generated_at: datetime
    date_from: date
    date_to: date
    days: int

    # Zone section
    total_floors: int
    total_zones: int
    floors: List[FloorSummary]

    # Device section
    total_devices: int
    total_sensors: int
    total_controllers: int
    devices_on: int
    devices_off: int
    devices: List[DeviceDetail]

    # Automation section
    total_schedules: int
    total_thresholds: int
    automations: List[AutomationDetail]

    # Activity section
    total_logs_in_period: int
    activity_breakdown: List[ActivityBreakdown]

    # Sensor history section
    sensor_history: List[SensorHistoryData] = []

    class Config:
        from_attributes = True