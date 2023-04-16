from pydantic import BaseSettings, RedisDsn


class CacheSettings(BaseSettings):
    max_connections: int = 10
    dsn: RedisDsn = f"redis://:redis@127.0.0.1:6379/3"

    class Config:
        env_prefix = "cache_"
