from pydantic import BaseModel

# Shared properties
class HomeBase(BaseModel):
    name: str

class HomeCreate(HomeBase):
    pass
class HomeResponse(HomeBase):
    id: int

    class Config:
        from_attributes = True