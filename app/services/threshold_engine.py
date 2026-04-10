import asyncio
from app.db.database import get_db_connection
from app.crud import crud_setting
from app.services import mqtt as mqtt_service
from app.utils import Utils

async def run_threshold_engine():
    while True:
        try:
            async for conn in get_db_connection():
                trigger_task = await crud_setting.get_triggered_thresholds(conn)
                for threshold in trigger_task:
                    target_status = '1' if threshold['action'] == 'ON' else '0'
                    feed_id = f"{threshold['target_feed_id']}-control"
                    device_name = threshold['target_device_name']
                    home_id = threshold['home_id']
                    current_sensor_value = threshold['current_sensor_value']
                    sensor_name = threshold['sensor_name']

                    mqtt_service.publish_command(feed_id, target_status)
                    description = f"'{sensor_name}' reached {current_sensor_value}. Automatically turned '{device_name}' to '{threshold['action']}'."
                    await Utils.generate_log(conn, description, "system action", home_id)
        except Exception as e:
            print(f"Error in threshold engine: {str(e)}")
        await asyncio.sleep(5)