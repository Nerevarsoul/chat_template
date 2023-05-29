import uuid

from fastapi import HTTPException, status
from pydantic.types import UUID4
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app import db
from app.db.enums import ChatState, ChatUserRole
from app.db.registry import registry
from app.schemas import chats as s_chat


def _get_contacts(contacts: list[UUID4], current_user_uid: UUID4) -> list[UUID4]:
    contacts.append(current_user_uid)
    unique_contacts = set(contacts)
    if len(unique_contacts) == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"contacts": "chat cannot be created with one user"}
        )
    return list(unique_contacts)


async def create_chat(data: s_chat.CreateChatData, current_user_uid: str) -> s_chat.CreateChatResponse:
    try:
        async with registry.session() as session:
            chat = db.Chat(state=ChatState.ACTIVE)

            session.add(chat)
            await session.flush()
            current_user_uid = uuid.UUID(current_user_uid)
            contacts = _get_contacts(contacts=data.contacts, current_user_uid=current_user_uid)
            for user_uid in contacts:
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

    return s_chat.CreateChatResponse(chat_id=chat.id, chat_name=data.chat_name, contacts=contacts)


async def get_chat_list(user_id):
    chat_subquery = (
        select(db.ChatRelationship.chat_id)
        .select_from(db.ChatRelationship)
        .where(db.ChatRelationship.user_uid == user_id)
        .order_by(db.ChatRelationship.chat_id)
        .subquery("chat_subquery")
    )

    query = (
        select(db.Chat)
        .options(selectinload(db.Chat.recipients))
        .join(chat_subquery, db.Chat.id == chat_subquery.c.chat_id)
    )

    async with registry.session() as session:
        chat_list = await session.execute(query)
        return [s_chat.Chat.from_orm(row) for row in chat_list.scalars()]
