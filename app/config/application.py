from typing import Any, Optional

from pydantic import BaseSettings, validator


class AppSettings(BaseSettings):
    name: str = "Chats"
    version: str = "0.1.0"
    docs_url: str = "/docs"
    root_path: str = ""

    debug: bool = False

    log_level: str = "DEBUG"
    log_sql_query_time: bool = True

    @validator("version", always=True)
    def version_validator(cls, value: Optional[str]) -> str:
        return value or "0.1.0"

    class Config:
        env_prefix = "app_"
