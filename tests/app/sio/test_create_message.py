import random
import uuid
from datetime import datetime
from unittest.mock import patch

import pytest
from sqlalchemy import func, select

from app.db.enums import ChatUserRole, MessageType
from app.db.models import ChatRelationship, Message
from app.db.registry import registry
from app.services import sio as sio_service
from app.sio.constants import NAMESPACE
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


@pytest.mark.usefixtures("clear_db")
async def test_create_empty_message(user_db_f, chat_db_f):
    user = await user_db_f.create()
    chat = await chat_db_f.create()
    new_message = NewMessageFactory.build(factory_use_construct=True, sender_id=user.uid, chat_id=chat.id, text="")

    with pytest.raises(Exception) as exc:
        await sio_service.process_message(new_message=new_message.model_dump(by_alias=True), sid=str(uuid.uuid4()))
    assert exc.typename == "ValidationError"

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == chat.id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 0


@pytest.mark.usefixtures("clear_db")
async def test_def_get_recipients_data(chat_relationship_db_f) -> None:
    chat_rel_1 = await chat_relationship_db_f.create(user_role=ChatUserRole.CREATOR)
    chat_rel_2 = await chat_relationship_db_f.create(chat__id=chat_rel_1.chat_id)

    recipients_uid = await sio_service._get_recipients_uid(chat_id=chat_rel_1.chat_id)

    assert len(recipients_uid) == 2
    assert str(chat_rel_1.user_uid) in recipients_uid
    assert str(chat_rel_2.user_uid) in recipients_uid


def test_get_online_recipiets_sid() -> None:
    recipints_uid = [str(uuid.uuid4()) for _ in range(4)]
    recipints_sid = [str(uuid.uuid4()) for _ in range(3)]
    recipients_data = {
        recipints_uid[0]: set(),
        recipints_uid[1]: {recipints_sid[0], recipints_sid[1]},
        recipints_uid[2]: set(),
        recipints_uid[3]: {recipints_sid[2]},
    }

    online_recipients_sid = sio_service._get_online_recipients_sid(recipients_data)

    assert sorted(recipints_sid) == sorted(online_recipients_sid)


def test_offline_recipiets_uid() -> None:
    recipints_uid = [str(uuid.uuid4()) for _ in range(4)]
    recipints_sid = [str(uuid.uuid4()) for _ in range(3)]
    recipients_data = {
        recipints_uid[0]: set(),
        recipints_uid[1]: {recipints_sid[0], recipints_sid[1]},
        recipints_uid[2]: set(),
        recipints_uid[3]: {recipints_sid[2]},
    }

    offline_recipiets_uid = sio_service._get_offline_recipients_uid(recipients_data)

    assert sorted([recipints_uid[0], recipints_uid[2]]) == sorted(offline_recipiets_uid)


async def test_def_send_online_mesage() -> None:
    count_of_recipients = random.randint(5, 10)
    recipients_sid = [str(uuid.uuid4()) for _ in range(count_of_recipients)]
    message = {"test": "mesasge"}
    event_name = "event:name"

    with patch("app.services.sio.sio.sio.emit") as sio_emit_mock:
        await sio_service._send_online_message(recipients_sid=recipients_sid, message=message, event_name=event_name)

    assert sio_emit_mock.await_count == count_of_recipients

    for sid in recipients_sid:
        sio_emit_mock.assert_any_await(event=event_name, data=message, to=sid, namespace=NAMESPACE)


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
