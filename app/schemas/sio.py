import enum

from pydantic import BaseModel, Field, validator
from pydantic.types import UUID4


class SioEvents(enum.StrEnum):
    USER_MISSING = "srv:user:missing"


class NewMessage(BaseModel):
    user_uid: UUID4 = Field(alias="sender_id")
    chat_id: int
    client_id: UUID4
    text: str

    @validator("text")
    def new_message_contains_only_spaces(cls, text: str) -> str:
        clear_text = text.strip()
        if not clear_text:
            raise ValueError("text must contain characters")
        return clear_text
