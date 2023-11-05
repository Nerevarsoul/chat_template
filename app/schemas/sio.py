import enum

from pydantic import BaseModel, Field, field_validator
from pydantic.types import UUID4


class SioEvents(enum.StrEnum):
    USER_MISSING = "srv:user:missing"
    MESSAGE_NEW = "srv:msg:new"
    MESSAGE_CHANGE = "srv:msg:change"
    TYPING = "srv:typing"


class BasePayload(BaseModel):
    user_uid: UUID4 = Field(alias="sender_id")
    chat_id: int
    client_id: UUID4


class NewMessagePayload(BasePayload):
    text: str

    @field_validator("text")
    def new_message_contains_only_spaces(cls, text: str) -> str:
        clear_text = text.strip()
        if not clear_text:
            raise ValueError("text must contain characters")
        return clear_text


class EditMessagePayload(NewMessagePayload):
    message_id: int


class DeleteMessagesPayload(BasePayload):
    message_ids: list[int]
