import uuid
from typing import TYPE_CHECKING

import pytest
from fastapi import status

from app import config
from app.main import app

if TYPE_CHECKING:
    from httpx import AsyncClient


async def test_get_chat_list_without_user_id(client: "AsyncClient") -> None:
    response = await client.get(app.other_asgi_app.url_path_for("get_chat_list"))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "User not found"}


@pytest.mark.usefixtures("clear_db")
async def test_get_chat_list_user_not_exist(client: "AsyncClient") -> None:
    user_uid = str(uuid.uuid4())
    response = await client.get(
        app.other_asgi_app.url_path_for("get_chat_list"), headers={config.application.user_header_name: user_uid}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "User not found"}


@pytest.mark.usefixtures("clear_db")
async def test_get_chat_list_empty(client: "AsyncClient", user_db_f) -> None:
    user_uid = str(uuid.uuid4())
    await user_db_f.create(uid=user_uid)

    response = await client.get(
        app.other_asgi_app.url_path_for("get_chat_list"), headers={config.application.user_header_name: user_uid}
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"result": []}
