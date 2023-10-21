import enum

from pydantic import BaseModel, Field, field_validator
from pydantic.types import UUID4


class SioEvents(enum.StrEnum):
    USER_MISSING = "srv:user:missing"
    NEW_MESSAGE = "srv:msg:new"
    CHANGE_MESSAGE = "srv:msg:change"


class NewMessage(BaseModel):
    user_uid: UUID4 = Field(alias="sender_id")
    chat_id: int
    client_id: UUID4
    text: str

    @field_validator("text")
    def new_message_contains_only_spaces(cls, text: str) -> str:
        clear_text = text.strip()
        if not clear_text:
            raise ValueError("text must contain characters")
        return clear_text


class EditMessageData(BaseModel):
    user_uid: UUID4 = Field(alias="sender_id")
    message_id: int
    chat_id: int
    client_id: UUID4
    text: str

    @field_validator("text")
    def edited_message_contains_only_spaces(cls, text: str) -> str:
        clear_text = text.strip()
        if not clear_text:
            raise ValueError("text must contain characters")
        return clear_text
