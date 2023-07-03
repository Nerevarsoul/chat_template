from pydantic import BaseSettings, RedisDsn


class CacheSettings(BaseSettings):
    max_connections: int = 10
    dsn: RedisDsn = ""

    class Config:
        env_prefix = "cache_"
