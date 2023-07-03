import redis.asyncio as redis

from app import config
from app.db.registry import registry

cache = redis.from_url(url=config.cache.dsn, max_connections=config.cache.max_connections)


async def services_setup() -> None:
    await registry.setup()


async def services_close() -> None:
    await registry.close()
    await cache.close()
