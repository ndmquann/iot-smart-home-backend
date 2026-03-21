from pydantic import BaseModel
from typing import Optional

# Shared properties
class ZoneBase(BaseModel):
    floor: int
    room: str

# Properties required to create a zone
class ZoneCreate(ZoneBase):
    pass

# Properties returned to client
class ZoneResponse(ZoneBase):
    id: int
    admin_id: Optional[int] = None