from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SettingBase(BaseModel):
    name: str
    admin_id: int
# ==========================================
# SCHEDULE SCHEMAS (Module 3)
# ==========================================
class ScheduleBase(SettingBase):
    date_start: datetime
    date_end: Optional[datetime] = None
    time_start: datetime
    timer: Optional[int] = None

class ScheduleCreate(ScheduleBase):
    type: str = "schedule"

class ScheduleResponse(ScheduleBase):
    setting_id: int
    type: str
    
    class Config:
        from_attributes = True


# ==========================================
# THRESHOLD SCHEMAS (Module 2)
# ==========================================
class ThresholdBase(SettingBase):
    value: float
    condition: bool # True: greater than, False: less than

class ThresholdCreate(ThresholdBase):
    type: str = "threshold"

class ThresholdResponse(ThresholdBase):
    setting_id: int
    type: str

    class Config:
        from_attributes = True