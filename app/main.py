import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.db.database import connect_to_db, close_db_connection
from app.api.v1.api import router
from app.core.exceptions import SmartHomeException

from app.services.mqtt import fastapi_loop, mqtt_client
import app.services.mqtt as mqtt_module
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_db()
    print("Database connected")
    
    mqtt_module.fastapi_loop = asyncio.get_running_loop()
    
    mqtt_client.connect(settings.AIO_SERVER, settings.AIO_PORT, 60)
    mqtt_client.loop_start()

    yield

    mqtt_client.loop_stop()
    mqtt_client.disconnect()

    await close_db_connection()
    print("Database disconnected")
    
app = FastAPI(title="Smart Home IoT Backend", lifespan=lifespan)

app.include_router(router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Smart Home IoT Backend!"}

@app.exception_handler(SmartHomeException)
async def smart_home_exception_handler(request: Request, exc: SmartHomeException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "error_code": exc.error_code,
            "message": exc.message}
    )