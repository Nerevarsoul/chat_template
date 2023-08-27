import pytest
from fastapi import status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select

from app import config
from app.db import Device
from app.db.registry import registry
from app.main import app
from app.schemas.contacts import PlatformName
from tests.factories.schemas import TokenDataFactory


@pytest.mark.usefixtures("clear_db")
@pytest.mark.parametrize(
    "request_body, field_name",
    [
        ({"device_type": PlatformName.ANDROID}, "token"),
        ({"token": "gfyudurtdckhjbjvty"}, "device_type"),
    ],
)
async def test_put_notifications_token_bad_request(
    user_db_f, client: "AsyncClient", request_body: dict, field_name: str
) -> None:
    user = await user_db_f.create()
    response = await client.post(
        app.other_asgi_app.url_path_for("put_notifications_token"),
        json=jsonable_encoder(request_body),
        headers={config.application.user_header_name: str(user.uid)},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": {field_name: "Field required"}}

    async with registry.session() as session:
        query = select(func.count()).select_from(Device).where(Device.user_uid == user.uid)
        quantity = (await session.execute(query)).scalar()
    assert quantity == 0


@pytest.mark.usefixtures("clear_db")
async def test_put_notifications_token(user_db_f, client: "AsyncClient") -> None:
    user = await user_db_f.create()
    response = await client.post(
        app.other_asgi_app.url_path_for("put_notifications_token"),
        json=jsonable_encoder(TokenDataFactory.build()),
        headers={config.application.user_header_name: str(user.uid)},
    )
    assert response.status_code == status.HTTP_200_OK

    async with registry.session() as session:
        query = select(func.count()).select_from(Device).where(Device.user_uid == user.uid)
        quantity = (await session.execute(query)).scalar()
    assert quantity == 1


@pytest.mark.usefixtures("clear_db")
async def test_put_notifications_token_retry(user_db_f, client: "AsyncClient") -> None:
    user = await user_db_f.create()
    response = await client.post(
        app.other_asgi_app.url_path_for("put_notifications_token"),
        json=jsonable_encoder(TokenDataFactory.build(device_type=PlatformName.IOS)),
        headers={config.application.user_header_name: str(user.uid)},
    )
    assert response.status_code == status.HTTP_200_OK

    response = await client.post(
        app.other_asgi_app.url_path_for("put_notifications_token"),
        json=jsonable_encoder(TokenDataFactory.build(device_type=PlatformName.IOS)),
        headers={config.application.user_header_name: str(user.uid)},
    )
    assert response.status_code == status.HTTP_200_OK

    async with registry.session() as session:
        query = select(func.count()).select_from(Device).where(Device.user_uid == user.uid)
        quantity = (await session.execute(query)).scalar()
    assert quantity == 1
