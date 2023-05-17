from uuid import UUID

from pydantic import BaseModel, Field


class CreateChatData(BaseModel):
    chat_name: str
    contacts: list[UUID] = Field(
        ..., min_items=2, unique_items=True, description="В чате должно быть как минимум два разных участника"
    )


class CreateChatResponse(BaseModel):
    chat_id: int
    chat_name: str
    contacts: list[UUID] = Field(..., min_items=2)
