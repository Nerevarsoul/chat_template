import uuid

import pytest

from app import config
from app.schemas.sio import SioEvents
from app.services import sio as sio_service


async def test_connect_with_unregistred_user():
    event = await sio_service.connect(
        "sid",
        {"asgi.scope": {"headers": [(config.application.user_header_name.encode(), str(uuid.uuid4()).encode())]}},
    )
    assert event == SioEvents.USER_NOT_FOUND


async def test_connect_without_user_header():
    event = await sio_service.connect("sid", {"asgi.scope": {"headers": []}})
    assert event == SioEvents.USER_MISSING


@pytest.mark.usefixtures("clear_db")
async def test_connect(user_db_f):
    user = await user_db_f.create()
    event = await sio_service.connect(
        "sid",
        {"asgi.scope": {"headers": [(config.application.user_header_name.encode(), str(user.uid).encode())]}},
    )
    assert event is None
