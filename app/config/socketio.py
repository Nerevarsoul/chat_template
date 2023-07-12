from pydantic_settings import BaseSettings, SettingsConfigDict

Seconds = int


class SocketioSettings(BaseSettings):
    ping_timeout: Seconds = 15
    ping_interval: Seconds = 10

    model_config = SettingsConfigDict(env_prefix="socketio_")

    # class Config:
    #     env_prefix = "socketio_"
