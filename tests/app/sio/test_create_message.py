import uuid
from datetime import datetime

import pytest
from fastapi import status
from sqlalchemy import func, select

from app.db.enums import MessageType
from app.db.models import ChatRelationship, Message
from app.db.registry import registry
from app.schemas import sio as s_sio
from app.services import cache as cache_service
from app.services import sio as sio_service
from tests.factories.schemas import SioNewMessagePayloadFactory


@pytest.mark.usefixtures("clear_cache")
@pytest.mark.usefixtures("clear_db")
async def test_create_message(chat_relationship_db_f, mocker):
    сhat_rel = await chat_relationship_db_f.create()
    sio_new_message_payload = SioNewMessagePayloadFactory.build(
        sender_id=сhat_rel.user_uid, chat_id=сhat_rel.chat_id
    ).model_dump(by_alias=True, mode="json")

    sid = str(uuid.uuid4())
    await cache_service.create_sid_cache(str(сhat_rel.user_uid), sid)

    send_online_message_mock = mocker.patch("app.services.sio._send_online_message")
    response_time = datetime.utcnow()
    await sio_service.process_create_message(sio_payload=sio_new_message_payload, sid=sid)

    send_online_message_mock.assert_awaited_once_with(
        message=sio_new_message_payload,
        recipients_sid=[sid],
        event_name=s_sio.SioEvents.MESSAGE_NEW,
    )
    saved_message_data = send_online_message_mock.await_args.kwargs["message"]
    saved_message_data_time_created = datetime.fromtimestamp(saved_message_data["time_created"])
    assert saved_message_data_time_created > response_time
    assert saved_message_data_time_created < datetime.utcnow()

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == сhat_rel.chat_id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 1

    async with registry.session() as session:
        query = select(Message).where(Message.chat_id == сhat_rel.chat_id)
        message = (await session.execute(query)).scalar()
    assert message.id == saved_message_data["id"]
    assert message.time_created == saved_message_data_time_created
    assert str(message.user_uid) == saved_message_data["sender_id"]
    assert message.chat_id == saved_message_data["chat_id"]
    assert message.text == sio_new_message_payload["text"]
    assert saved_message_data["text"] == sio_new_message_payload["text"]
    assert message.type_ == MessageType.FROM_USER


@pytest.mark.usefixtures("clear_cache")
@pytest.mark.usefixtures("clear_db")
async def test_retry_create_message(chat_relationship_db_f, message_db_f, mocker):
    сhat_rel = await chat_relationship_db_f.create()
    sio_new_message_payload = SioNewMessagePayloadFactory.build(
        sender_id=сhat_rel.user_uid, chat_id=сhat_rel.chat_id
    ).model_dump(by_alias=True, mode="json")
    await message_db_f.create(
        user_uid=сhat_rel.user_uid, chat_id=сhat_rel.chat_id, client_id=sio_new_message_payload["client_id"]
    )

    sid = str(uuid.uuid4())
    await cache_service.create_sid_cache(str(сhat_rel.user_uid), sid)

    send_message_mock = mocker.patch("app.services.sio._send_message")
    await sio_service.process_create_message(sio_payload=sio_new_message_payload, sid=sid)
    send_message_mock.assert_not_awaited()

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == сhat_rel.chat_id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 1


@pytest.mark.usefixtures("clear_cache")
@pytest.mark.usefixtures("clear_db")
async def test_create_empty_message(chat_relationship_db_f, mocker):
    сhat_rel = await chat_relationship_db_f.create()
    sio_new_message_payload = SioNewMessagePayloadFactory.build(
        factory_use_construct=True, sender_id=сhat_rel.user_uid, chat_id=сhat_rel.chat_id, text=""
    ).model_dump(by_alias=True, mode="json")

    sid = str(uuid.uuid4())
    await cache_service.create_sid_cache(str(сhat_rel.user_uid), sid)

    send_message_mock = mocker.patch("app.services.sio._send_message")
    with pytest.raises(Exception) as exc:
        await sio_service.process_create_message(sio_payload=sio_new_message_payload, sid=sid)
    assert exc.typename == "ValidationError"
    assert "text must contain characters" in str(exc.value)
    send_message_mock.assert_not_awaited()

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == сhat_rel.chat_id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 0


@pytest.mark.usefixtures("clear_cache")
@pytest.mark.usefixtures("clear_db")
async def test_update_unread_counter(chat_relationship_db_f, mocker):
    chat_rel1 = await chat_relationship_db_f.create(unread_counter=2)
    chat_id = chat_rel1.chat_id
    chat_rel2 = await chat_relationship_db_f.create(chat__id=chat_id, unread_counter=5)
    sio_new_message_payload = SioNewMessagePayloadFactory.build(
        sender_id=chat_rel1.user_uid, chat_id=chat_id
    ).model_dump(by_alias=True, mode="json")

    sid = str(uuid.uuid4())
    await cache_service.create_sid_cache(str(chat_rel1.user_uid), sid)

    send_message_mock = mocker.patch("app.services.sio._send_message")
    await sio_service.process_create_message(sio_payload=sio_new_message_payload, sid=sid)
    send_message_mock.assert_awaited_once()

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


@pytest.mark.usefixtures("clear_cache")
@pytest.mark.usefixtures("clear_db")
async def test_retry_update_unread_counter(chat_relationship_db_f, mocker):
    chat_rel1 = await chat_relationship_db_f.create()
    chat_id = chat_rel1.chat_id
    chat_rel2 = await chat_relationship_db_f.create(chat__id=chat_id)

    sio_new_message_payload = SioNewMessagePayloadFactory.build(
        sender_id=chat_rel1.user_uid, chat_id=chat_id
    ).model_dump(by_alias=True, mode="json")

    sid = str(uuid.uuid4())
    await cache_service.create_sid_cache(str(chat_rel1.user_uid), sid)

    send_message_mock = mocker.patch("app.services.sio._send_message")
    await sio_service.process_create_message(sio_payload=sio_new_message_payload, sid=sid)
    await sio_service.process_create_message(sio_payload=sio_new_message_payload, sid=sid)
    send_message_mock.assert_awaited_once()

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
async def test_create_message_from_other_user(chat_relationship_db_f, mocker):
    chat_rel = await chat_relationship_db_f.create()
    chat_rel_2 = await chat_relationship_db_f.create(chat_id=chat_rel.chat_id)
    sio_new_message_payload = SioNewMessagePayloadFactory.build(
        sender_id=chat_rel_2.user_uid, chat_id=chat_rel.chat_id
    ).model_dump(by_alias=True, mode="json")

    sid = str(uuid.uuid4())
    await cache_service.create_sid_cache(str(chat_rel.user_uid), sid)

    send_message_mock = mocker.patch("app.services.sio._send_message")
    with pytest.raises(Exception) as exc:
        await sio_service.process_create_message(sio_payload=sio_new_message_payload, sid=sid)
    assert exc.typename == "HTTPException"
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    send_message_mock.assert_not_awaited()

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == chat_rel.chat_id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 0
