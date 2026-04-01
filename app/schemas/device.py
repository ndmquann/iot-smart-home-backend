from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Shared properties
class DeviceBase(BaseModel):
    name: str
    feed_id: str
    zone_id: int

# Properties required to create a device
class DeviceCreate(DeviceBase):
    type: str # must be "controller" or "sensor"
    status: Optional[str] = "OFF"

# Properties returned to frontend
class DeviceResponse(DeviceBase):
    id: int
    admin_id: Optional[int] = None
    status: str
    type: str
    value: Optional[float] = None # display only for sensors

    class Config:
        from_attributes = True
        
class SensorHistoryResponse(BaseModel):
    value: float
    timestamp: datetime

    class Config:
        from_attributes = True