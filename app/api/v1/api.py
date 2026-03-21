from fastapi import APIRouter
from app.api.v1.endpoints import users, zones, devices, logs, settings, auth

router = APIRouter()

router.include_router(users.router, prefix="/users", tags=["Users"])
router.include_router(zones.router, prefix="/zones", tags=["Zones"])
router.include_router(devices.router, prefix="/devices", tags=["Devices"])
router.include_router(logs.router, prefix="/logs", tags=["Logs"])
router.include_router(settings.router, prefix="/settings", tags=["Settings"])
router.include_router(auth.router, prefix="/auth", tags=["Auth"])