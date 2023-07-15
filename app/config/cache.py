from pydantic import RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class CacheSettings(BaseSettings):
    max_connections: int = 10
    dsn: RedisDsn = ""  # type: ignore[assignment]

    user_sid_cache_lifetime: int = 2 * 60 * 60

    model_config = SettingsConfigDict(env_prefix="cache_")
