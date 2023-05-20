from fastapi import status

from app.schemas.chats import CreateChatData, CreateChatResponse
from fastapi import APIRouter, Depends
from pydantic.types import UUID4

from app.services import chats as chats_service
from app.services.utils import get_current_user

router = APIRouter()


@router.post("/create", response_model=CreateChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(data: CreateChatData):
    create_chat_response = await chats_service.create_chat(data)
    return create_chat_response


@router.get("/chat/management/list")
async def get_chat_list(user_uid: UUID4 = Depends(get_current_user)):
    chat_list = await chats_service.get_chat_list(user_uid)
    return {"result": chat_list}
