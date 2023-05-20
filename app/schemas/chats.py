from uuid import UUID

from pydantic import BaseModel, Field

from app.db.enums import ChatState, ChatUserRole


class CreateChatData(BaseModel):
    chat_name: str
    contacts: list[UUID] = Field(
        ..., min_items=2, unique_items=True, description="В чате должно быть как минимум два разных участника"
    )


class CreateChatResponse(BaseModel):
    chat_id: int
    chat_name: str
    contacts: list[UUID] = Field(..., min_items=2)


class Chat(BaseModel):
    id: int
    state: ChatState
    chat_name: str
    user_chat_state: ChatState
    user_role: ChatUserRole
