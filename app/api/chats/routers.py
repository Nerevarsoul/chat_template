from fastapi import APIRouter, HTTPException, status

from app.api.chats.schemas import CreateChatData, CreateChatResponse
from app.api.chats.services import users_exist
from app.db.enums import ChatState, ChatUserRole
from app.db.models import Chat, ChatRelationship
from app.db.registry import registry

router = APIRouter()


@router.post("/create", response_model=CreateChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(data: CreateChatData):
    if not await users_exist(data.contacts):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    async with registry.session() as session:
        chat = Chat(state=ChatState.ACTIVE.value)

        session.add(chat)
        await session.flush()
        user_role = ChatUserRole.CREATOR.value
        for user_uid in data.contacts:
            chat_relationships = ChatRelationship(
                user_uid=user_uid,
                chat_id=chat.id,
                chat_name=data.chat_name,
                state=ChatState.ACTIVE.value,
                user_role=user_role,
            )
            user_role = ChatUserRole.USER.value
            session.add(chat_relationships)

        await session.commit()

    response = CreateChatResponse(chat_id=chat.id, chat_name=data.chat_name, contacts=data.contacts)

    return response
