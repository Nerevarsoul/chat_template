from typing import AsyncGenerator, Generator

import pytest

from alembic.command import downgrade, upgrade
from alembic.config import Config as AlembicConfig
from app.clients import services_close, services_setup
from app.config import database as db_config


@pytest.fixture(autouse=True)
async def _registry() -> AsyncGenerator[None, None]:
    await services_setup()
    yield
    await services_close()


@pytest.fixture(autouse=True, scope="session")
def migrate_db() -> Generator[None, None, None]:
    if db_config.dsn.path != "/test":
        raise RuntimeError("Migration for tests should be applied only on test DB")

    config = AlembicConfig("alembic.ini")

    upgrade(config, "head")
    yield
    downgrade(config, "base")
