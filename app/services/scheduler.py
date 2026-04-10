import asyncio
import asyncpg
from datetime import datetime
from app.crud import crud_setting
from app.db.database import get_db_connection
from app.services import mqtt as mqtt_service

async def run_scheduler():
    now = datetime.now()
    await asyncio.sleep(60 - now.second)

    while True:
        try:
            curr_time = datetime.now()
            async for conn in get_db_connection():
                start_task = await crud_setting.get_due_start_schedules(conn, curr_time)

                for task in start_task:
                    target_status = '1' if task['action'] == 'ON' else '0'
                    feed_id = f"{task['feed_id']}-control"

                    mqtt_service.publish_command(feed_id, target_status)
                
                end_task = await crud_setting.get_due_end_schedules(conn, curr_time)

                for task in end_task:
                    target_status = "0" if task['action'] == "ON" else "1"
                    feed_id = f"{task['feed_id']}-control"

                    mqtt_service.publish_command(feed_id, target_status)
        except Exception as e:
            print(f"Error in scheduler: {str(e)}")

        now = datetime.now()
        sleep_duration = 60 - now.second
        await asyncio.sleep(sleep_duration)