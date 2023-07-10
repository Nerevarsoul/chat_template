from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app import config
from app.config.types import AsyncDBDsn


class _DBRegistry:
    engine: AsyncEngine
    session: Callable[..., Session]

    def __init__(
        self,
        dsn: AsyncDBDsn,
        pool_size: int = config.database.pool_size,
        pool_max_overflow: int = config.database.pool_max_overflow,
        pool_recycle: int = config.database.pool_recycle,
        pool_timeout: int = config.database.pool_timeout,
    ):
        self.dsn = dsn
        self.pool_size = pool_size
        self.pool_max_overflow = pool_max_overflow
        self.pool_recycle = pool_recycle
        self.pool_timeout = pool_timeout
        self.base = declarative_base()

    async def setup(self) -> None:
        self.engine = create_async_engine(
            self.dsn.clear_dsn,
            connect_args={"server_settings": self.dsn.server_settings},
            poolclass=AsyncAdaptedQueuePool,
            pool_size=self.pool_size,
            max_overflow=self.pool_max_overflow,
            pool_recycle=self.pool_recycle,
            pool_timeout=self.pool_timeout,
        )
        self.session = sessionmaker(  # type: ignore[call-overload]
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            class_=AsyncSession,
            bind=self.engine,
        )

    async def close(self) -> None:
        await self.engine.dispose()


registry = _DBRegistry(config.database.dsn)
