import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.db.database import connect_to_db, close_db_connection
from app.api.v1.api import router
from app.core.exceptions import SmartHomeException

from app.services.mqtt import fastapi_loop, mqtt_client
import app.services.mqtt as mqtt_module
from app.services.scheduler import run_scheduler
from app.services.threshold_engine import run_threshold_engine
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_db()
    print("Database connected")
    
    mqtt_module.fastapi_loop = asyncio.get_running_loop()
    
    mqtt_client.connect(settings.AIO_SERVER, settings.AIO_PORT, 60)
    mqtt_client.loop_start()
    scheduler_task = asyncio.create_task(run_scheduler())
    threshold_task = asyncio.create_task(run_threshold_engine())

    yield
    
    for task, name in [(scheduler_task, "Scheduler"), (threshold_task, "Threshold engine")]:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                print(f"{name} task cancelled")

    mqtt_client.loop_stop()
    mqtt_client.disconnect()

    await close_db_connection()
    print("Database disconnected")
    
app = FastAPI(title="Smart Home IoT Backend", lifespan=lifespan)

# 1. Define the exact local addresses allowed to connect
origins = [
    "http://localhost",
    "http://localhost:8000",   # Default for Python http.server
    "http://127.0.0.1:8000",   
    "http://localhost:5500",   # Default for VS Code Live Server
    "http://127.0.0.1:5500",
]

# 2. Apply the restricted list to your middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # <--- Changed from ["*"] to origins
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

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