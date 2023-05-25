from pydantic import BaseModel, Field, validator
from pydantic.types import UUID4

from app.db.enums import ChatState, ChatUserRole

__all__ = (
    "CreateChatData",
    "CreateChatResponse",
    "Chat",
)


class CreateChatData(BaseModel):
    chat_name: str
    contacts: list[UUID4] = Field(
        ..., min_items=2, unique_items=True, description="В чате должно быть как минимум два разных участника"
    )

    @validator("chat_name")
    def chat_name_contains_only_spaces(cls, chat_name: str) -> str:
        clear_chat_name = chat_name.strip()
        if not clear_chat_name:
            raise ValueError("chat name must contain characters")
        return clear_chat_name


class CreateChatResponse(BaseModel):
    chat_id: int
    chat_name: str
    contacts: list[UUID4] = Field(..., min_items=2)


class Recipient(BaseModel):
    user_uid: UUID4
    chat_name: str
    state: ChatState
    user_role: ChatUserRole

    class Config:
        orm_mode = True


class Chat(BaseModel):
    id: int
    state: ChatState
    recipients: list[Recipient]

    class Config:
        orm_mode = True
