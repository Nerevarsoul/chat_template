import uuid
from datetime import datetime

import pytest
from fastapi import status
from sqlalchemy import and_, func, select

from app.db.enums import MessageType
from app.db.models import Message
from app.db.registry import registry
from app.services import cache as cache_service
from app.services import sio as sio_service
from tests.factories.schemas import DeleteMessagesDataFactory


@pytest.mark.usefixtures("clear_db")
async def test_delete_one_message(chat_relationship_db_f, message_db_f):
    chat_rel = await chat_relationship_db_f.create()
    message = await message_db_f.create(user_uid=chat_rel.user_uid, chat_id=chat_rel.chat_id)
    message_for_delete = DeleteMessagesDataFactory.build(
        sender_id=chat_rel.user_uid, message_ids=[message.id], chat_id=chat_rel.chat_id
    )

    response_time = datetime.utcnow()
    deleted_message_data = await sio_service._delete_messages(message_for_delete=message_for_delete)

    assert len(deleted_message_data) == 1

    async with registry.session() as session:
        query = (
            select(func.count())
            .select_from(Message)
            .where(and_(Message.chat_id == chat_rel.chat_id, Message.type_ == MessageType.DELETED))
        )
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 1

    async with registry.session() as session:
        query = select(Message).where(Message.id == message.id)
        deleted_message = (await session.execute(query)).scalar()

    assert deleted_message.id == deleted_message_data[0].id
    assert deleted_message_data[0].time_updated > response_time
    assert deleted_message_data[0].time_updated < datetime.utcnow()
    assert deleted_message.time_updated == deleted_message_data[0].time_updated
    assert deleted_message.text == sio_service.DELETED_MESSAGE_TEXT
    assert deleted_message.type_ == MessageType.DELETED


@pytest.mark.usefixtures("clear_db")
async def test_delete_a_few_messages(chat_relationship_db_f, message_db_f):
    messages_count = 3
    chat_rel = await chat_relationship_db_f.create()
    messages = message_db_f.create_batch(messages_count, user_uid=chat_rel.user_uid, chat_id=chat_rel.chat_id)
    message_ids = [(await message).id for message in messages]
    message_for_delete = DeleteMessagesDataFactory.build(
        sender_id=chat_rel.user_uid, message_ids=message_ids, chat_id=chat_rel.chat_id
    )

    response_time = datetime.utcnow()
    deleted_messages_data = await sio_service._delete_messages(message_for_delete=message_for_delete)

    assert len(deleted_messages_data) == messages_count

    async with registry.session() as session:
        query = (
            select(func.count())
            .select_from(Message)
            .where(and_(Message.chat_id == chat_rel.chat_id, Message.type_ == MessageType.DELETED))
        )
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == messages_count

    for deleted_message_raw in deleted_messages_data:
        async with registry.session() as session:
            query = select(Message).where(Message.id == deleted_message_raw.id)
            deleted_message = (await session.execute(query)).scalar()

        assert deleted_message_raw.id in message_ids
        assert deleted_message_raw.time_updated > response_time
        assert deleted_message_raw.time_updated < datetime.utcnow()
        assert deleted_message.time_updated == deleted_message_raw.time_updated
        assert deleted_message.text == sio_service.DELETED_MESSAGE_TEXT
        assert deleted_message.type_ == MessageType.DELETED


@pytest.mark.usefixtures("clear_db")
async def test_retry_delete_message(chat_relationship_db_f, message_db_f):
    chat_rel = await chat_relationship_db_f.create()
    message = await message_db_f.create(
        user_uid=chat_rel.user_uid, chat_id=chat_rel.chat_id, type_=MessageType.DELETED
    )
    message_for_delete = DeleteMessagesDataFactory.build(
        sender_id=chat_rel.user_uid, message_ids=[message.id], chat_id=chat_rel.chat_id
    )

    deleted_message_data = await sio_service._delete_messages(message_for_delete=message_for_delete)

    assert len(deleted_message_data) == 0

    async with registry.session() as session:
        query = (
            select(func.count())
            .select_from(Message)
            .where(and_(Message.chat_id == chat_rel.chat_id, Message.type_ == MessageType.DELETED))
        )
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 1


@pytest.mark.usefixtures("clear_cache")
@pytest.mark.usefixtures("clear_db")
async def test_delete_message_with_wrong_sender_id(chat_relationship_db_f, message_db_f):
    chat_rel = await chat_relationship_db_f.create()
    message = await message_db_f.create(user_uid=chat_rel.user_uid, chat_id=chat_rel.chat_id)
    message_for_delete = DeleteMessagesDataFactory.build(
        sender_id=uuid.uuid4(), message_ids=[message.id], chat_id=chat_rel.chat_id
    )

    sid = str(uuid.uuid4())
    await cache_service.create_sid_cache(str(chat_rel.user_uid), sid)

    with pytest.raises(Exception) as exc:
        await sio_service.process_delete_messages(
            message=message_for_delete.model_dump(by_alias=True, mode="json"), sid=sid
        )
    assert exc.typename == "HTTPException"
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST

    async with registry.session() as session:
        query = (
            select(func.count())
            .select_from(Message)
            .where(and_(Message.chat_id == chat_rel.chat_id, Message.type_ == MessageType.DELETED))
        )
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 0


@pytest.mark.usefixtures("clear_cache")
@pytest.mark.usefixtures("clear_db")
async def test_delete_other_user_message(chat_relationship_db_f, message_db_f):
    chat_rel = await chat_relationship_db_f.create()
    chat_rel_2 = await chat_relationship_db_f.create(chat_id=chat_rel.chat_id)
    message = await message_db_f.create(user_uid=chat_rel.user_uid, chat_id=chat_rel.chat_id)
    message_for_delete = DeleteMessagesDataFactory.build(
        sender_id=chat_rel_2.user_uid, message_ids=[message.id], chat_id=chat_rel.chat_id
    )

    sid = str(uuid.uuid4())
    await cache_service.create_sid_cache(str(chat_rel_2.user_uid), sid)

    with pytest.raises(Exception) as exc:
        await sio_service.process_delete_messages(
            message=message_for_delete.model_dump(by_alias=True, mode="json"), sid=sid
        )
    assert exc.typename == "HTTPException"
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND

    async with registry.session() as session:
        query = (
            select(func.count())
            .select_from(Message)
            .where(and_(Message.chat_id == chat_rel.chat_id, Message.type_ == MessageType.DELETED))
        )
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 0
