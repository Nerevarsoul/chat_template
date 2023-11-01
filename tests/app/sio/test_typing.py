import uuid

import pytest

from app.schemas import sio as s_sio
from app.services import cache as cache_service
from app.services import sio as sio_service
from tests.factories.schemas import EditMessageDataFactory


@pytest.mark.usefixtures("clear_cache")
@pytest.mark.usefixtures("clear_db")
async def test_typing(chat_relationship_db_f, mocker):
    chat_rel = await chat_relationship_db_f.create()

    sio_typing_message = EditMessageDataFactory.build(
        sender_id=chat_rel.user_uid, chat_id=chat_rel.chat_id
    ).model_dump(by_alias=True, mode="json")

    sid = str(uuid.uuid4())
    await cache_service.create_sid_cache(str(chat_rel.user_uid), sid)

    send_message_mock = mocker.patch("app.services.sio._send_message")

    sio_typing_message_response = await sio_service.process_typing(message=sio_typing_message, sid=sid)
    assert sio_typing_message_response is None

    send_message_mock.assert_awaited_once_with(
        message=sio_typing_message,
        chat_id=chat_rel.chat_id,
        sender_uid=str(chat_rel.user_uid),
        event_name=s_sio.SioEvents.TYPING,
        sid=sid,
    )
