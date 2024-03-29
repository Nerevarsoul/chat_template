from datetime import datetime

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.types import UUID4

from app import config
from app.db.enums import ChatState, ChatUserRole, MessageType

__all__ = (
    "CreateChatData",
    "CreateChatResponse",
    "Chat",
    "ManageRecipientsData",
)


class CreateChatData(BaseModel):
    chat_name: str
    contacts: list[UUID4]

    @field_validator("chat_name")
    def chat_name_contains_only_spaces(cls, chat_name: str) -> str:
        clear_chat_name = chat_name.strip()
        if not clear_chat_name:
            raise ValueError("chat name must contain characters")
        return clear_chat_name

    def add_contact(self, user_uid: UUID4) -> None:
        self.contacts.append(user_uid)
        unique_contacts = set(self.contacts)
        if len(unique_contacts) == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail={"contacts": "chat cannot be created with one user"}
            )
        self.contacts = list(unique_contacts)


class CreateChatResponse(BaseModel):
    chat_id: int
    chat_name: str
    contacts: list[UUID4] = Field(..., min_length=2)


class User(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)


class Recipient(BaseModel):
    user_uid: UUID4
    chat_name: str
    state: ChatState
    user_role: ChatUserRole
    user: None | User = None

    model_config = ConfigDict(from_attributes=True)


class Chat(BaseModel):
    id: int
    state: ChatState
    recipients: list[Recipient]

    model_config = ConfigDict(from_attributes=True)


class ManageRecipientsData(BaseModel):
    chat_id: int
    contacts: list[UUID4]


class Message(BaseModel):
    id: int
    user_uid: UUID4
    chat_id: int
    client_id: UUID4
    text: str
    search_text: str
    type_: MessageType
    quoted_message: None
    mentions: None
    links: None
    original_id: None
    original_chat_id: None
    time_created: datetime
    time_updated: None

    model_config = ConfigDict(from_attributes=True)


class GetMessageHistoryData(BaseModel):
    chat_id: int
    message_id: int = 0
    page_size: int = config.application.message_history_page_size
    look_forward: bool = False
    include_message: bool = False
