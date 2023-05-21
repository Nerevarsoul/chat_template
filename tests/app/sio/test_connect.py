import uuid

from app import config
from app.schemas.sio import SioEvents
from app.services import sio as sio_service


async def test_connect():
    event = await sio_service.connect(
        "sid",
        {"asgi.scope": {"headers": [(config.application.user_header_name.encode(), str(uuid.uuid4()).encode())]}},
    )
    assert event is None


async def test_connect_without_user_header():
    event = await sio_service.connect("sid", {"asgi.scope": {"headers": []}})
    assert event == SioEvents.USER_MISSING
