from pydantic.networks import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class DBSettings(BaseSettings):
    pool_size: int = 5
    pool_max_overflow: int = 5
    pool_recycle: int = 29
    pool_timeout: int = 10

    dsn: PostgresDsn = ""  # type: ignore[assignment]

    model_config = SettingsConfigDict(env_prefix="databases_")
