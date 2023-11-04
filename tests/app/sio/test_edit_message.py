import uuid
from datetime import datetime

import pytest
from fastapi import status
from sqlalchemy import func, select

from app.db.models import Message
from app.db.registry import registry
from app.schemas import sio as s_sio
from app.services import cache as cache_service
from app.services import sio as sio_service
from tests.factories.schemas import SioEditMessagePayloadFactory


@pytest.mark.usefixtures("clear_cache")
@pytest.mark.usefixtures("clear_db")
async def test_edit_message(chat_relationship_db_f, message_db_f, mocker):
    chat_rel = await chat_relationship_db_f.create()
    message = await message_db_f.create(user_uid=chat_rel.user_uid, chat_id=chat_rel.chat_id)
    sio_edit_message_payload = SioEditMessagePayloadFactory.build(
        sender_id=chat_rel.user_uid, message_id=message.id, chat_id=chat_rel.chat_id
    ).model_dump(by_alias=True, mode="json")

    sid = str(uuid.uuid4())
    await cache_service.create_sid_cache(str(chat_rel.user_uid), sid)

    send_online_message_mock = mocker.patch("app.services.sio._send_online_message")
    response_time = datetime.utcnow()
    await sio_service.process_edit_message(sio_payload=sio_edit_message_payload, sid=sid)

    send_online_message_mock.assert_awaited_once_with(
        message=sio_edit_message_payload,
        recipients_sid=[sid],
        event_name=s_sio.SioEvents.MESSAGE_CHANGE,
    )
    edited_message_data = send_online_message_mock.await_args.kwargs["message"]
    edited_message_data_time_updated = datetime.fromtimestamp(edited_message_data["time_updated"])
    assert edited_message_data_time_updated > response_time
    assert edited_message_data_time_updated < datetime.utcnow()

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == chat_rel.chat_id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 1

    async with registry.session() as session:
        query = select(Message).where(Message.id == message.id)
        db_message = (await session.execute(query)).scalar()
    assert db_message.time_created == message.time_created
    assert db_message.time_updated == edited_message_data_time_updated
    assert str(db_message.user_uid) == sio_edit_message_payload["sender_id"]
    assert db_message.chat_id == sio_edit_message_payload["chat_id"]
    assert db_message.text == sio_edit_message_payload["text"]
    assert db_message.type_ == message.type_


@pytest.mark.usefixtures("clear_cache")
@pytest.mark.usefixtures("clear_db")
async def test_retry_edit_message(chat_relationship_db_f, message_db_f, mocker):
    chat_rel = await chat_relationship_db_f.create()
    message = await message_db_f.create(user_uid=chat_rel.user_uid, chat_id=chat_rel.chat_id)
    sio_edit_message_payload = SioEditMessagePayloadFactory.build(
        sender_id=chat_rel.user_uid, message_id=message.id, chat_id=chat_rel.chat_id
    ).model_dump(by_alias=True, mode="json")

    sid = str(uuid.uuid4())
    await cache_service.create_sid_cache(str(chat_rel.user_uid), sid)

    send_online_message_mock = mocker.patch("app.services.sio._send_online_message")
    await sio_service.process_edit_message(sio_payload=sio_edit_message_payload, sid=sid)
    response_time = datetime.utcnow()
    await sio_service.process_edit_message(sio_payload=sio_edit_message_payload, sid=sid)

    assert send_online_message_mock.await_count == 2
    send_online_message_mock.assert_awaited_with(
        message=sio_edit_message_payload,
        recipients_sid=[sid],
        event_name=s_sio.SioEvents.MESSAGE_CHANGE,
    )
    edited_message_data = send_online_message_mock.await_args.kwargs["message"]
    edited_message_data_time_updated = datetime.fromtimestamp(edited_message_data["time_updated"])
    assert edited_message_data_time_updated > response_time
    assert edited_message_data_time_updated < datetime.utcnow()

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == chat_rel.chat_id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 1


@pytest.mark.usefixtures("clear_cache")
@pytest.mark.usefixtures("clear_db")
async def test_edit_to_empty_message(chat_relationship_db_f, message_db_f, mocker):
    chat_rel = await chat_relationship_db_f.create()
    message = await message_db_f.create(user_uid=chat_rel.user_uid, chat_id=chat_rel.chat_id)
    sio_edit_message_payload = SioEditMessagePayloadFactory.build(
        factory_use_construct=True,
        sender_id=chat_rel.user_uid,
        message_id=message.id,
        chat_id=chat_rel.chat_id,
        text="",
    ).model_dump(by_alias=True, mode="json")

    sid = str(uuid.uuid4())
    await cache_service.create_sid_cache(str(chat_rel.user_uid), sid)

    send_message_mock = mocker.patch("app.services.sio._send_message")
    with pytest.raises(Exception) as exc:
        await sio_service.process_edit_message(sio_payload=sio_edit_message_payload, sid=sid)
    assert exc.typename == "ValidationError"
    assert "text must contain characters" in str(exc.value)
    send_message_mock.assert_not_awaited()

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == sio_edit_message_payload["chat_id"])
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 1

    async with registry.session() as session:
        query = select(Message).where(Message.id == sio_edit_message_payload["message_id"])
        message = (await session.execute(query)).scalar()
    assert message.time_created == message.time_created
    assert message.time_updated is None
    assert message.user_uid == message.user_uid
    assert message.chat_id == message.chat_id
    assert message.text == message.text
    assert message.type_ == message.type_


@pytest.mark.usefixtures("clear_cache")
@pytest.mark.usefixtures("clear_db")
async def test_edit_message_with_wrong_sender_id(chat_relationship_db_f, message_db_f, mocker):
    chat_rel = await chat_relationship_db_f.create()
    message = await message_db_f.create(user_uid=chat_rel.user_uid, chat_id=chat_rel.chat_id)
    sio_edit_message_payload = SioEditMessagePayloadFactory.build(
        sender_id=uuid.uuid4(), message_id=message.id, chat_id=chat_rel.chat_id
    ).model_dump(by_alias=True, mode="json")

    sid = str(uuid.uuid4())
    await cache_service.create_sid_cache(str(chat_rel.user_uid), sid)

    send_message_mock = mocker.patch("app.services.sio._send_message")
    with pytest.raises(Exception) as exc:
        await sio_service.process_edit_message(sio_payload=sio_edit_message_payload, sid=sid)
    assert exc.typename == "HTTPException"
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    send_message_mock.assert_not_awaited()

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == sio_edit_message_payload["chat_id"])
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 1

    async with registry.session() as session:
        query = select(Message).where(Message.id == sio_edit_message_payload["message_id"])
        message = (await session.execute(query)).scalar()
    assert message.time_created == message.time_created
    assert message.time_updated is None
    assert message.user_uid == message.user_uid
    assert message.chat_id == message.chat_id
    assert message.text == message.text
    assert message.type_ == message.type_


@pytest.mark.usefixtures("clear_cache")
@pytest.mark.usefixtures("clear_db")
async def test_edit_other_user_message(chat_relationship_db_f, message_db_f, mocker):
    chat_rel = await chat_relationship_db_f.create()
    chat_rel_2 = await chat_relationship_db_f.create(chat_id=chat_rel.chat_id)
    message = await message_db_f.create(user_uid=chat_rel.user_uid, chat_id=chat_rel.chat_id)
    sio_edit_message_payload = SioEditMessagePayloadFactory.build(
        sender_id=chat_rel_2.user_uid, message_id=message.id, chat_id=chat_rel.chat_id
    ).model_dump(by_alias=True, mode="json")

    sid = str(uuid.uuid4())
    await cache_service.create_sid_cache(str(chat_rel_2.user_uid), sid)

    send_message_mock = mocker.patch("app.services.sio._send_message")
    with pytest.raises(Exception) as exc:
        await sio_service.process_edit_message(sio_payload=sio_edit_message_payload, sid=sid)
    assert exc.typename == "HTTPException"
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    send_message_mock.assert_not_awaited()

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == sio_edit_message_payload["chat_id"])
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 1

    async with registry.session() as session:
        query = select(Message).where(Message.id == sio_edit_message_payload["message_id"])
        message = (await session.execute(query)).scalar()
    assert message.time_created == message.time_created
    assert message.time_updated is None
    assert message.user_uid == message.user_uid
    assert message.chat_id == message.chat_id
    assert message.text == message.text
    assert message.type_ == message.type_
