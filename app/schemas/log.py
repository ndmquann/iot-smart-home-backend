from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Based properties
class LogBase(BaseModel):
    type: str # ['user action', 'admin action', 'system action', 'sensor alert']
    description: str

# Properties returned to frontend for activity history
class LogResponse(LogBase):
    id: int
    timestamp: datetime

    # optional fields populated dynamically based on the mapping tables
    user_name: Optional[str] = None
    device_name: Optional[str] = None
    setting_name: Optional[str] = None