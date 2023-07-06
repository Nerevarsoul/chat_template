from fastapi import APIRouter, Depends, status
from pydantic.types import UUID4

from app.schemas import chats as s_chat
from app.services import chats as chats_service
from app.services.utils import get_current_user

router = APIRouter()


@router.post("/create", response_model=s_chat.CreateChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    data: s_chat.CreateChatData, current_user_uid: UUID4 = Depends(get_current_user)
) -> s_chat.CreateChatResponse:
    return await chats_service.create_chat(data, current_user_uid)


@router.get("/chat/management/list")
async def get_chat_list(user_uid: UUID4 = Depends(get_current_user)) -> list[s_chat.Chat]:
    return await chats_service.get_chat_list(user_uid)


@router.get("/recipients")
async def get_chat_recipients(chat_id: int, user_uid: UUID4 = Depends(get_current_user)) -> list[s_chat.Recipient]:
    return await chats_service.get_chat_recipients(chat_id=chat_id, user_uid=user_uid)


@router.post("/add_recipients")
async def add_recipients(data: s_chat.AddRecipientsData, user_uid: UUID4 = Depends(get_current_user)) -> dict:
    return await chats_service.add_recipients(data, user_uid)


@router.post("/delete_recipients")
async def delete_recipients(data: s_chat.DeleteRecipientsData, user_uid: UUID4 = Depends(get_current_user)) -> dict:
    return await chats_service.delete_recipients(data, user_uid)
