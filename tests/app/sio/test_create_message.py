import uuid
from datetime import datetime

import pytest
from fastapi import status
from sqlalchemy import func, select

from app.db.enums import MessageType
from app.db.models import ChatRelationship, Message
from app.db.registry import registry
from app.services import cache as cache_service
from app.services import sio as sio_service
from tests.factories.schemas import NewMessageFactory


@pytest.mark.usefixtures("clear_db")
async def test_create_message(user_db_f, chat_db_f):
    user = await user_db_f.create()
    chat = await chat_db_f.create()
    new_message = NewMessageFactory.build(sender_id=user.uid, chat_id=chat.id)

    response_time = datetime.utcnow()
    saved_message_data = await sio_service._save_message(message_for_saving=new_message)
    assert saved_message_data[1] > response_time
    assert saved_message_data[1] < datetime.utcnow()

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == chat.id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 1

    async with registry.session() as session:
        query = select(Message).where(Message.chat_id == chat.id)
        message = (await session.execute(query)).scalar()
    assert message.id == saved_message_data[0]
    assert message.time_created == saved_message_data[1]
    assert message.user_uid == user.uid
    assert message.chat_id == chat.id
    assert message.text == new_message.text
    assert message.type_ == MessageType.FROM_USER


@pytest.mark.usefixtures("clear_db")
async def test_retry_create_message(user_db_f, chat_db_f, message_db_f):
    user = await user_db_f.create()
    chat = await chat_db_f.create()

    new_message = NewMessageFactory.build(sender_id=user.uid, chat_id=chat.id)
    await message_db_f.create(user_uid=user.uid, chat_id=chat.id, client_id=new_message.client_id)

    saved_message_data = await sio_service._save_message(message_for_saving=new_message)
    assert saved_message_data is None

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == chat.id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 1


@pytest.mark.usefixtures("clear_cache")
@pytest.mark.usefixtures("clear_db")
async def test_create_empty_message(user_db_f, chat_db_f):
    user = await user_db_f.create()
    chat = await chat_db_f.create()
    new_message = NewMessageFactory.build(factory_use_construct=True, sender_id=user.uid, chat_id=chat.id, text="")

    sid = str(uuid.uuid4())
    await cache_service.create_sid_cache(str(user.uid), sid)

    with pytest.raises(Exception) as exc:
        await sio_service.process_create_message(message=new_message.model_dump(by_alias=True, mode="json"), sid=sid)
    assert exc.typename == "ValidationError"
    assert "text must contain characters" in str(exc.value)

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == chat.id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 0


@pytest.mark.usefixtures("clear_db")
async def test_update_unread_counter(chat_relationship_db_f):
    chat_rel1 = await chat_relationship_db_f.create(unread_counter=2)
    chat_id = chat_rel1.chat_id
    chat_rel2 = await chat_relationship_db_f.create(chat__id=chat_id, unread_counter=5)

    new_message = NewMessageFactory.build(sender_id=chat_rel1.user_uid, chat_id=chat_id)

    saved_message_data = await sio_service._save_message(message_for_saving=new_message)
    assert saved_message_data is not None

    async with registry.session() as session:
        query = select(ChatRelationship).where(ChatRelationship.chat_id == chat_id)
        db_chat_rels = (await session.execute(query)).scalars()

    for db_chat_rel in db_chat_rels:
        if db_chat_rel.user_uid == chat_rel1.user_uid:
            assert db_chat_rel.unread_counter == 2
        elif db_chat_rel.user_uid == chat_rel2.user_uid:
            assert db_chat_rel.unread_counter == 6
        else:
            raise


@pytest.mark.usefixtures("clear_db")
async def test_retry_update_unread_counter(chat_relationship_db_f):
    chat_rel1 = await chat_relationship_db_f.create()
    chat_id = chat_rel1.chat_id
    chat_rel2 = await chat_relationship_db_f.create(chat__id=chat_id)

    new_message = NewMessageFactory.build(sender_id=chat_rel1.user_uid, chat_id=chat_id)

    saved_message_data = await sio_service._save_message(message_for_saving=new_message)
    assert saved_message_data is not None

    saved_message_data = await sio_service._save_message(message_for_saving=new_message)
    assert saved_message_data is None

    async with registry.session() as session:
        query = select(ChatRelationship).where(ChatRelationship.chat_id == chat_id)
        db_chat_rels = (await session.execute(query)).scalars()

    for db_chat_rel in db_chat_rels:
        if db_chat_rel.user_uid == chat_rel1.user_uid:
            assert db_chat_rel.unread_counter == 0
        elif db_chat_rel.user_uid == chat_rel2.user_uid:
            assert db_chat_rel.unread_counter == 1
        else:
            raise


@pytest.mark.usefixtures("clear_cache")
@pytest.mark.usefixtures("clear_db")
async def test_create_message_from_other_user(chat_relationship_db_f):
    chat_rel = await chat_relationship_db_f.create()
    chat_rel_2 = await chat_relationship_db_f.create(chat_id=chat_rel.chat_id)
    new_message = NewMessageFactory.build(sender_id=chat_rel_2.user_uid, chat_id=chat_rel.chat_id)

    sid = str(uuid.uuid4())
    await cache_service.create_sid_cache(str(chat_rel.user_uid), sid)

    with pytest.raises(Exception) as exc:
        await sio_service.process_create_message(message=new_message.model_dump(by_alias=True, mode="json"), sid=sid)
    assert exc.typename == "HTTPException"
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == chat_rel.chat_id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 0
