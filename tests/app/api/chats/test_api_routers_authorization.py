import uuid
from typing import TYPE_CHECKING

import pytest
from fastapi import status

from app import config
from app.main import app

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.parametrize(
    "view_name,method",
    [
        ("create_chat", "POST"),
        ("get_chat_list", "GET"),
        ("get_chat_recipients", "GET"),
        ("add_recipients", "POST"),
        ("delete_recipients", "POST"),
    ],
)
async def test_request_without_user_id(client: "AsyncClient", view_name, method: str) -> None:
    response = await client.request(method=method, url=app.other_asgi_app.url_path_for(view_name))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "User not found"}


@pytest.mark.parametrize(
    "view_name,method",
    [
        ("create_chat", "POST"),
        ("get_chat_list", "GET"),
        ("get_chat_recipients", "GET"),
        ("add_recipients", "POST"),
        ("delete_recipients", "POST"),
    ],
)
async def test_request_with_user_not_exist(client: "AsyncClient", view_name: str, method: str) -> None:
    user_uid = str(uuid.uuid4())
    response = await client.request(
        method=method,
        url=app.other_asgi_app.url_path_for(view_name),
        headers={config.application.user_header_name: user_uid},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "User not found"}
