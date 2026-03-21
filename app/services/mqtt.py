import paho.mqtt.client as mqtt
import asyncio
from app.core.config import settings
from app.db import database
from app.crud import crud_device
from app.core.exceptions import NotFoundException

fastapi_loop = None

def on_connect(client, userdata, flags, rc):
    """Connect to Adafruit IO MQTT broker."""
    if rc == 0:
        print("Successfullt connected to Adafruit IO MQTT broker")
        client.subscribe(f"{settings.ADAFRUIT_AIO_USERNAME}/feeds/#")
    else:
        print("Failed to connect, return code %d\n", rc)

def on_message(client, userdata, msg):
    """Handle incoming MQTT messages."""
    topic = msg.topic
    payload = msg.payload.decode("utf-8")
    if (topic.endswith("/json") 
        or topic.endswith("/csv") 
        or topic.split("/")[-1].isdigit()):
        return
    
    feed_id = topic.split("/")[-1]

    print(f"Received MQTT message - Feed: {feed_id}, | Value: {payload}")

    if fastapi_loop and database.db_pool:
        asyncio.run_coroutine_threadsafe(
            process_mqtt_message(feed_id, payload),
            fastapi_loop
        )

async def process_mqtt_message(feed_id: str, payload: str):
    """Process incoming MQTT messages."""
    async with database.db_pool.acquire() as conn:
        try:
            device = await crud_device.get_device_by_feed_id(conn, feed_id)

            if not device:
                raise NotFoundException(feed_id)
            
            if device['type'] == "sensor":
                sensor_value = float(payload)
                await crud_device.update_sensor_value(conn, feed_id, sensor_value)
                print(f"Sensor value updated - Feed: {feed_id}, | Value: {sensor_value}")
            
            elif device['type'] == "controller":
                status = 'on' if payload == '1' else 'off'
                await crud_device.update_device_status(conn, feed_id, status)
                print(f"Controller status updated - Feed: {feed_id}, | Status: {payload}")

        except Exception as e:
            print(f"Failed to process MQTT message: {str(e)}")
    
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(settings.ADAFRUIT_AIO_USERNAME, settings.ADAFRUIT_AIO_KEY)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def publish_command(feed_id: str, command: str):
    topic = f"{settings.ADAFRUIT_AIO_USERNAME}/feeds/{feed_id}"
    mqtt_client.publish(topic, command)
    print(f"Published MQTT command - Feed: {feed_id}, | Command: {command}")