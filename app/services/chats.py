from fastapi import HTTPException, status
from pydantic.types import UUID4
from sqlalchemy import and_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app import db
from app.db.enums import ChatState, ChatUserRole
from app.db.registry import registry
from app.schemas import chats as s_chat


async def create_chat(data: s_chat.CreateChatData, current_user_uid: UUID4) -> s_chat.CreateChatResponse:
    try:
        async with registry.session() as session:
            chat = db.Chat(state=ChatState.ACTIVE)
            session.add(chat)
            await session.flush()

            data.add_contact(user_uid=current_user_uid)
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

    return s_chat.CreateChatResponse(chat_id=chat.id, chat_name=data.chat_name, contacts=data.contacts)


async def get_chat_list(from_archive: bool, user_id: UUID4) -> list[s_chat.Chat]:
    condition = db.ChatRelationship.user_uid == user_id

    if from_archive:
        condition &= db.ChatRelationship.state == ChatState.ARCHIVE
    else:
        condition &= db.ChatRelationship.state == ChatState.ACTIVE

    chat_subquery = (
        select(db.ChatRelationship.chat_id)
        .select_from(db.ChatRelationship)
        .where(condition)
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
        return [s_chat.Chat.model_validate(row) for row in chat_list.scalars()]


async def get_chat_recipients(chat_id: int, user_uid: UUID4) -> list[s_chat.Recipient]:
    query = select(db.ChatRelationship).where(
        and_(db.ChatRelationship.chat_id == chat_id, db.ChatRelationship.state != ChatState.DELETED)
    )
    async with registry.session() as session:
        chat_recipients = await session.execute(query)
        chat_recipients = [s_chat.Recipient.model_validate(row) for row in chat_recipients.scalars()]
    if not chat_recipients:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if user_uid not in [recipient.user_uid for recipient in chat_recipients]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
    return chat_recipients


async def add_recipients(data: s_chat.ManageRecipientsData, user_uid: UUID4) -> s_chat.ChatApiResponse:
    chat_recipients = await get_chat_recipients(data.chat_id, user_uid)
    chat_recipients_uids = [recipient.user_uid for recipient in chat_recipients]
    new_recipients_uids = [contact_uid for contact_uid in data.contacts if contact_uid not in chat_recipients_uids]
    if not new_recipients_uids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"contacts": "all contacts already in chat"}
        )
    for chat_recipient in chat_recipients:
        if chat_recipient.user_role == ChatUserRole.CREATOR:
            chat_name = chat_recipient.chat_name
    try:
        async with registry.session() as session:
            for recipient_uid in new_recipients_uids:
                chat_relationships = db.ChatRelationship(
                    user_uid=recipient_uid,
                    chat_id=data.chat_id,
                    chat_name=chat_name,
                    state=ChatState.ACTIVE,
                    user_role=ChatUserRole.USER,
                )
                session.add(chat_relationships)
            await session.commit()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"contacts": "one of contacts is not exist"}
        )
    return s_chat.ChatApiResponse(result=s_chat.Result(success=True))


async def delete_recipients(data: s_chat.ManageRecipientsData, user_uid: UUID4) -> s_chat.ChatApiResponse:
    chat_recipients = await get_chat_recipients(data.chat_id, user_uid)
    chat_recipients_uids = [recipient.user_uid for recipient in chat_recipients]
    recipients_uids_for_delete = [contact_uid for contact_uid in data.contacts if contact_uid in chat_recipients_uids]
    if not recipients_uids_for_delete:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"contacts": "all contacts not in chat"})
    if len(chat_recipients_uids) - len(recipients_uids_for_delete) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"contacts": "only one user will remain in the chat"}
        )
    try:
        async with registry.session() as session:
            query = (
                update(db.ChatRelationship)
                .values(state=ChatState.DELETED)
                .where(
                    and_(
                        db.ChatRelationship.user_uid.in_(recipients_uids_for_delete),
                        db.ChatRelationship.chat_id == data.chat_id,
                    )
                )
            )
            await session.execute(query)
            await session.commit()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"contacts": "one of contacts is not exist"}
        )
    return s_chat.ChatApiResponse(result=s_chat.Result(success=True))


async def archive_chat(chat_id: int, user_uid: UUID4) -> s_chat.ChatApiResponse:
    async with registry.session() as session:
        update_query = (
            update(db.ChatRelationship)
            .values(state=ChatState.ARCHIVE)
            .where(
                and_(
                    db.ChatRelationship.user_uid == user_uid,
                    db.ChatRelationship.chat_id == chat_id,
                )
            )
        )
        result = await session.execute(update_query)
        if not result.rowcount:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        await session.commit()

    return s_chat.ChatApiResponse(result=s_chat.Result(success=True))


async def unarchive_chat(chat_id: int, user_uid: UUID4) -> s_chat.ChatApiResponse:
    async with registry.session() as session:
        update_query = (
            update(db.ChatRelationship)
            .values(state=ChatState.ACTIVE)
            .where(
                and_(
                    db.ChatRelationship.user_uid == user_uid,
                    db.ChatRelationship.chat_id == chat_id,
                )
            )
        )
        result = await session.execute(update_query)
        if not result.rowcount:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        await session.commit()

    return s_chat.ChatApiResponse(result=s_chat.Result(success=True))


async def pin_chat(chat_id: int, user_uid: UUID4) -> s_chat.ChatApiResponse:
    async with registry.session() as session:
        update_query = (
            update(db.ChatRelationship)
            .values(is_pinned=True)
            .where(
                and_(
                    db.ChatRelationship.user_uid == user_uid,
                    db.ChatRelationship.chat_id == chat_id,
                )
            )
        )
        result = await session.execute(update_query)
        if not result.rowcount:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        await session.commit()

    return s_chat.ChatApiResponse(result=s_chat.Result(success=True))


async def unpin_chat(chat_id: int, user_uid: UUID4) -> s_chat.ChatApiResponse:
    async with registry.session() as session:
        update_query = (
            update(db.ChatRelationship)
            .values({"is_pinned": False, "time_pinned": None})
            .where(
                and_(
                    db.ChatRelationship.user_uid == user_uid,
                    db.ChatRelationship.chat_id == chat_id,
                )
            )
        )
        result = await session.execute(update_query)
        if not result.rowcount:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        await session.commit()

    return s_chat.ChatApiResponse(result=s_chat.Result(success=True))
