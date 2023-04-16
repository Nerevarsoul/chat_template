from pydantic import BaseSettings


Seconds = int


class SocketioSettings(BaseSettings):
    ping_timeout: Seconds = 15
    ping_interval: Seconds = 10

    class Config:
        env_prefix = "socketio_"
