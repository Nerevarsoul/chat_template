from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    name: str = "Chats"
    version: str = "0.1.0"
    docs_url: str = "/docs"
    root_path: str = ""

    debug: bool = False

    log_level: str = "DEBUG"
    log_sql_query_time: bool = True

    user_header_name: str = "user-id"
    message_history_page_size: int = 20

    @field_validator("version", mode="before")
    def version_validator(cls, value: Optional[str]) -> str:
        return value or "0.1.0"

    model_config = SettingsConfigDict(env_prefix="app_")
