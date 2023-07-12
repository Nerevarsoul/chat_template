from pydantic_settings import BaseSettings, SettingsConfigDict

from .types import AsyncDBDsn


class DBSettings(BaseSettings):
    pool_size: int = 5
    pool_max_overflow: int = 5
    pool_recycle: int = 29
    pool_timeout: int = 10

    dsn: AsyncDBDsn = ""  # type: ignore[assignment]

    model_config = SettingsConfigDict(env_prefix="databases_")
    # class Config:
    #     env_prefix = "databases_"
