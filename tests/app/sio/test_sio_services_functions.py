import random
import uuid
from unittest.mock import patch

import pytest

from app.db.enums import ChatUserRole
from app.services import sio as sio_service
from app.sio.constants import NAMESPACE


@pytest.mark.usefixtures("clear_db")
async def test_get_recipients_data(chat_relationship_db_f) -> None:
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

    assert set(recipints_sid) == set(online_recipients_sid)


def test_get_offline_recipiets_uid() -> None:
    recipints_uid = [str(uuid.uuid4()) for _ in range(4)]
    recipints_sid = [str(uuid.uuid4()) for _ in range(3)]
    recipients_data = {
        recipints_uid[0]: set(),
        recipints_uid[1]: {recipints_sid[0], recipints_sid[1]},
        recipints_uid[2]: set(),
        recipints_uid[3]: {recipints_sid[2]},
    }

    offline_recipiets_uid = sio_service._get_offline_recipients_uid(recipients_data)

    assert set([recipints_uid[0], recipints_uid[2]]) == set(offline_recipiets_uid)


async def test_send_online_mesage() -> None:
    count_of_recipients = random.randint(5, 10)
    recipients_sid = [str(uuid.uuid4()) for _ in range(count_of_recipients)]
    message = {"test": "mesasge"}
    event_name = "event:name"

    with patch("app.services.sio.sio.sio.emit") as sio_emit_mock:
        await sio_service._send_online_message(recipients_sid=recipients_sid, message=message, event_name=event_name)

    assert sio_emit_mock.await_count == count_of_recipients

    for sid in recipients_sid:
        sio_emit_mock.assert_any_await(event=event_name, data=message, to=sid, namespace=NAMESPACE)
