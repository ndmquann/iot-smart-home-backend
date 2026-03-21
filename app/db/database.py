import asyncpg
from app.core.config import settings

db_pool = None

async def connect_to_db():
    global db_pool
    db_pool = await asyncpg.create_pool(
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_SERVER,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB
    )

async def close_db_connection():
    global db_pool
    if db_pool:
        await db_pool.close()

async def get_db_connection():
    async with db_pool.acquire() as connection:
        yield connection