from typing import AsyncGenerator

import pytest
from sqlalchemy.sql import text

from app.clients import cache
from app.db import Chat, ChatRelationship, Message, User
from app.db.registry import registry as db_registry

TRUNCATE_QUERY = "TRUNCATE TABLE {tbl_name} CASCADE;"


@pytest.fixture
async def clear_db() -> AsyncGenerator[None, None]:
    yield
    async with db_registry.engine.begin() as conn:
        await conn.execute(text(TRUNCATE_QUERY.format(tbl_name=ChatRelationship.__tablename__)))
        await conn.execute(text(TRUNCATE_QUERY.format(tbl_name=Chat.__tablename__)))
        await conn.execute(text(TRUNCATE_QUERY.format(tbl_name=User.__tablename__)))
        await conn.execute(text(TRUNCATE_QUERY.format(tbl_name=Message.__tablename__)))


@pytest.fixture
async def clear_cache() -> AsyncGenerator[None, None]:
    yield
    await cache.flushdb()
