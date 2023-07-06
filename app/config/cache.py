from pydantic import BaseSettings, RedisDsn


class CacheSettings(BaseSettings):
    max_connections: int = 10
    dsn: RedisDsn = ""  # type: ignore[assignment]

    user_sid_cache_lifetime: int = 2 * 60 * 60

    class Config:
        env_prefix = "cache_"
