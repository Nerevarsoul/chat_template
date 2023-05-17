from fastapi import APIRouter, status

from app.schemas.chats import CreateChatData, CreateChatResponse
from app.services import chats as chats_service

router = APIRouter()


@router.post("/create", response_model=CreateChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(data: CreateChatData):
    create_chat_response = await chats_service.create_chat(data)
    return create_chat_response
