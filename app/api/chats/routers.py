from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.chats.schemas import CreateChatData, CreateChatResponse
from app.db.enums import ChatState, ChatUserRole
from app.db.models import Chat, ChatRelationship
from app.db.registry import registry

router = APIRouter()


@router.post("/create", response_model=CreateChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(data: CreateChatData):
    try:
        async with registry.session() as session:
            chat = Chat(state=ChatState.ACTIVE)

            session.add(chat)
            await session.flush()
            current_user_uid = data.contacts[0]
            for user_uid in data.contacts:
                if user_uid == current_user_uid:
                    user_role = ChatUserRole.CREATOR.value
                else:
                    user_role = ChatUserRole.USER
                chat_relationships = ChatRelationship(
                    user_uid=user_uid,
                    chat_id=chat.id,
                    chat_name=data.chat_name,
                    state=ChatState.ACTIVE,
                    user_role=user_role,
                )
                session.add(chat_relationships)

            await session.commit()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    response = CreateChatResponse(chat_id=chat.id, chat_name=data.chat_name, contacts=data.contacts)

    return response
