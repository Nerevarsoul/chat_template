import uuid
from datetime import datetime

import pytest
from fastapi import status
from sqlalchemy import func, select

from app.db.models import Message
from app.db.registry import registry
from app.services import cache as cache_service
from app.services import sio as sio_service
from tests.factories.schemas import EditMessageDataFactory


@pytest.mark.usefixtures("clear_db")
async def test_edit_message(chat_relationship_db_f, message_db_f):
    chat_rel = await chat_relationship_db_f.create()
    message = await message_db_f.create(user_uid=chat_rel.user_uid, chat_id=chat_rel.chat_id)
    edited_message = EditMessageDataFactory.build(
        sender_id=chat_rel.user_uid, message_id=message.id, chat_id=chat_rel.chat_id
    )

    response_time = datetime.utcnow()
    edited_message_data = await sio_service._update_message(message_for_update=edited_message)
    assert edited_message_data[0] > response_time
    assert edited_message_data[0] < datetime.utcnow()

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == edited_message.chat_id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 1

    async with registry.session() as session:
        query = select(Message).where(Message.id == edited_message.message_id)
        message = (await session.execute(query)).scalar()
    assert message.time_created == message.time_created
    assert message.time_updated == edited_message_data[0]
    assert message.user_uid == edited_message.user_uid
    assert message.chat_id == edited_message.chat_id
    assert message.text == edited_message.text
    assert message.type_ == message.type_


@pytest.mark.usefixtures("clear_db")
async def test_retry_edit_message(chat_relationship_db_f, message_db_f):
    chat_rel = await chat_relationship_db_f.create()
    message = await message_db_f.create(user_uid=chat_rel.user_uid, chat_id=chat_rel.chat_id)
    edited_message = EditMessageDataFactory.build(
        sender_id=chat_rel.user_uid, message_id=message.id, chat_id=chat_rel.chat_id
    )

    await sio_service._update_message(message_for_update=edited_message)
    response_time = datetime.utcnow()
    edited_message_data = await sio_service._update_message(message_for_update=edited_message)
    assert edited_message_data[0] > response_time
    assert edited_message_data[0] < datetime.utcnow()

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == edited_message.chat_id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 1


@pytest.mark.usefixtures("clear_cache")
@pytest.mark.usefixtures("clear_db")
async def test_edit_to_empty_message(chat_relationship_db_f, message_db_f):
    chat_rel = await chat_relationship_db_f.create()
    message = await message_db_f.create(user_uid=chat_rel.user_uid, chat_id=chat_rel.chat_id)
    edited_message = EditMessageDataFactory.build(
        factory_use_construct=True,
        sender_id=chat_rel.user_uid,
        message_id=message.id,
        chat_id=chat_rel.chat_id,
        text="",
    )

    sid = str(uuid.uuid4())
    await cache_service.create_sid_cache(str(chat_rel.user_uid), sid)

    with pytest.raises(Exception) as exc:
        await sio_service.process_edit_message(
            edited_message=edited_message.model_dump(by_alias=True, mode="json"), sid=sid
        )
    assert exc.typename == "ValidationError"
    assert "text must contain characters" in str(exc.value)

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == edited_message.chat_id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 1

    async with registry.session() as session:
        query = select(Message).where(Message.id == edited_message.message_id)
        message = (await session.execute(query)).scalar()
    assert message.time_created == message.time_created
    assert message.time_updated is None
    assert message.user_uid == message.user_uid
    assert message.chat_id == message.chat_id
    assert message.text == message.text
    assert message.type_ == message.type_


@pytest.mark.usefixtures("clear_cache")
@pytest.mark.usefixtures("clear_db")
async def test_edit_message_with_wrong_sender_id(chat_relationship_db_f, message_db_f):
    chat_rel = await chat_relationship_db_f.create()
    message = await message_db_f.create(user_uid=chat_rel.user_uid, chat_id=chat_rel.chat_id)
    edited_message = EditMessageDataFactory.build(
        sender_id=uuid.uuid4(), message_id=message.id, chat_id=chat_rel.chat_id
    )

    sid = str(uuid.uuid4())
    await cache_service.create_sid_cache(str(chat_rel.user_uid), sid)

    with pytest.raises(Exception) as exc:
        await sio_service.process_edit_message(
            edited_message=edited_message.model_dump(by_alias=True, mode="json"), sid=sid
        )
    assert exc.typename == "HTTPException"
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == edited_message.chat_id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 1

    async with registry.session() as session:
        query = select(Message).where(Message.id == edited_message.message_id)
        message = (await session.execute(query)).scalar()
    assert message.time_created == message.time_created
    assert message.time_updated is None
    assert message.user_uid == message.user_uid
    assert message.chat_id == message.chat_id
    assert message.text == message.text
    assert message.type_ == message.type_


@pytest.mark.usefixtures("clear_cache")
@pytest.mark.usefixtures("clear_db")
async def test_edit_other_user_message(chat_relationship_db_f, message_db_f):
    chat_rel = await chat_relationship_db_f.create()
    chat_rel_2 = await chat_relationship_db_f.create(chat_id=chat_rel.chat_id)
    message = await message_db_f.create(user_uid=chat_rel.user_uid, chat_id=chat_rel.chat_id)
    edited_message = EditMessageDataFactory.build(
        sender_id=chat_rel_2.user_uid, message_id=message.id, chat_id=chat_rel.chat_id
    )

    sid = str(uuid.uuid4())
    await cache_service.create_sid_cache(str(chat_rel_2.user_uid), sid)

    edited_message_data = await sio_service.process_edit_message(
        edited_message=edited_message.model_dump(by_alias=True, mode="json"), sid=sid
    )
    assert edited_message_data is None

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == edited_message.chat_id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 1

    async with registry.session() as session:
        query = select(Message).where(Message.id == edited_message.message_id)
        message = (await session.execute(query)).scalar()
    assert message.time_created == message.time_created
    assert message.time_updated is None
    assert message.user_uid == message.user_uid
    assert message.chat_id == message.chat_id
    assert message.text == message.text
    assert message.type_ == message.type_
