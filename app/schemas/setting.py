from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# ==========================================
# SCHEDULE SCHEMAS (Module 3)
# ==========================================
class ScheduleCreate(BaseModel):
    name: str
    date_start: datetime
    date_end: Optional[datetime] = None
    time_start: datetime
    timer: Optional[int] = None
    type: str = "schedule"

class ScheduleResponse(ScheduleCreate):
    sid: int
    type: str
    name: str
    date_start: datetime
    date_end: Optional[datetime] = None
    time_start: datetime
    timer: Optional[int] = None

# ==========================================
# THRESHOLD SCHEMAS (Module 2)
# ==========================================
class ThresholdCreate(BaseModel):
    name: str
    value: float
    condition: bool # True: greater than, False: less than
    type: str = "threshold"

class ThresholdResponse(ThresholdCreate):
    sid: int
    type: str
    name: str
    value: float
    condition: bool