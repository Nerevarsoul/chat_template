from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import db
from app.db.enums import ChatState, ChatUserRole
from app.db.registry import registry
from app.schemas.chats import CreateChatData, CreateChatResponse


async def create_chat(data: CreateChatData) -> CreateChatResponse:
    try:
        async with registry.session() as session:
            chat = db.Chat(state=ChatState.ACTIVE)

            session.add(chat)
            await session.flush()
            current_user_uid = data.contacts[0]
            for user_uid in data.contacts:
                if user_uid == current_user_uid:
                    user_role = ChatUserRole.CREATOR.value
                else:
                    user_role = ChatUserRole.USER
                chat_relationships = db.ChatRelationship(
                    user_uid=user_uid,
                    chat_id=chat.id,
                    chat_name=data.chat_name,
                    state=ChatState.ACTIVE,
                    user_role=user_role,
                )
                session.add(chat_relationships)

            await session.commit()
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    create_chat_response = CreateChatResponse(chat_id=chat.id, chat_name=data.chat_name, contacts=data.contacts)

    return create_chat_response


async def get_chat_list(user_id):
    query = (
        select(
            db.Chat.id,
            db.Chat.state,
            db.ChatRelationship.chat_name,
            db.ChatRelationship.state.label("user_chat_state"),
            db.ChatRelationship.user_role,
        )
        .outerjoin(db.ChatRelationship)
        .where(db.ChatRelationship.user_uid == user_id)
    )

    async with registry.session() as session:
        chat_list = (await session.execute(query)).scalars().all()

        return chat_list
