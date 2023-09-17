import random
import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select

from app.db import Message
from app.db.enums import ChatUserRole, MessageType
from app.db.registry import registry
from app.services import sio as sio_service
from app.sio import sio
from app.sio.constants import NAMESPACE
from tests.factories.schemas import NewMessageFactory


@pytest.mark.usefixtures("clear_db")
async def test_create_message(user_db_f, chat_db_f):
    user = await user_db_f.create()
    chat = await chat_db_f.create()
    new_message = NewMessageFactory.build(sender_id=user.uid, chat_id=chat.id)

    saved_message = await sio_service._save_message(message_for_saving=new_message)

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == chat.id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 1

    assert saved_message.user_uid == user.uid
    assert saved_message.chat_id == chat.id
    assert saved_message.text == new_message.text
    assert saved_message.type_ == MessageType.FROM_USER


@pytest.mark.usefixtures("clear_db")
async def test_retry_create_message(user_db_f, chat_db_f, message_db_f):
    user = await user_db_f.create()
    chat = await chat_db_f.create()

    new_message = NewMessageFactory.build(sender_id=user.uid, chat_id=chat.id)
    await message_db_f.create(user_uid=user.uid, chat_id=chat.id, client_id=new_message.client_id)

    saved_message = await sio_service._save_message(message_for_saving=new_message)
    assert saved_message is None

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == chat.id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 1


@pytest.mark.usefixtures("clear_db")
async def test_create_empty_message(user_db_f, chat_db_f):
    user = await user_db_f.create()
    chat = await chat_db_f.create()
    new_message = NewMessageFactory.build(factory_use_construct=True, sender_id=user.uid, chat_id=chat.id, text="")
    mock = AsyncMock(sio)

    with pytest.raises(Exception) as exc:
        await sio_service.process_message(
            sio=mock, new_message=new_message.model_dump(by_alias=True), sid=str(uuid.uuid4())
        )
    assert exc.typename == "ValidationError"

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == chat.id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 0


@pytest.mark.usefixtures("clear_db")
async def test_def_get_recipients_uid(chat_relationship_db_f) -> None:
    chat_rel_1 = await chat_relationship_db_f.create(user_role=ChatUserRole.CREATOR)
    chat_rel_2 = await chat_relationship_db_f.create(chat__id=chat_rel_1.chat_id)

    recipints_uid = await sio_service._get_recipients_uid(chat_id=chat_rel_1.chat_id)

    assert len(recipints_uid) == 2
    assert str(chat_rel_1.user_uid) in recipints_uid
    assert str(chat_rel_2.user_uid) in recipints_uid


async def test_def_send_online_mesage() -> None:
    mock = AsyncMock(sio)
    count_of_recipients = random.randint(5, 10)
    recipients_sid = [str(uuid.uuid4()) for _ in range(count_of_recipients)]
    message = {"test": "mesasge"}
    event_name = "event:name"

    await sio_service._send_online_message(
        sio=mock, recipients_sid=recipients_sid, message=message, event_name=event_name
    )

    assert mock.emit.await_count == count_of_recipients

    for sid in recipients_sid:
        mock.emit.assert_any_await(event=event_name, data=message, to=sid, namespace=NAMESPACE)
