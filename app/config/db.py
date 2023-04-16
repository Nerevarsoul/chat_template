from pydantic import BaseSettings

from .types import AsyncDBDsn


class DBSettings(BaseSettings):
    pool_size: int = 5
    pool_max_overflow: int = 5
    pool_recycle: int = 29
    pool_timeout: int = 10
    schema: str = "bot"

    dsn: AsyncDBDsn = ""

    class Config:
        env_prefix = "databases_"
