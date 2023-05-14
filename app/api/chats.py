from fastapi import APIRouter, Depends
from pydantic.types import UUID4

from app.services import chats as chats_service
from app.services.utils import get_current_user

router = APIRouter()


@router.get("/chat/management/list")
async def get_chat_list(user_uid: UUID4 = Depends(get_current_user)):
    chat_list = await chats_service.get_chat_list(user_uid)
    return {"result": chat_list}
