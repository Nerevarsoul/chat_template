from pydantic import BaseSettings, RedisDsn


class CacheSettings(BaseSettings):
    max_connections: int = 10
    dsn: RedisDsn = ""  # type: ignore[assignment]

    class Config:
        env_prefix = "cache_"
