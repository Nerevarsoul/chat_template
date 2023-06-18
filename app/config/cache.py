from pydantic import BaseSettings, RedisDsn

redis_dsn = RedisDsn.build(password="redis", port="6379", host="127.0.0.1", scheme="redis", path="/3")


class CacheSettings(BaseSettings):
    max_connections: int = 10
    dsn: RedisDsn = redis_dsn

    class Config:
        env_prefix = "cache_"
