import uuid
from typing import TYPE_CHECKING

import pytest
from fastapi import status

from app import config
from app.main import app
from tests.app.api.chats.utils import generate_chat_history

if TYPE_CHECKING:
    from httpx import AsyncClient


async def test_get_chat_list_without_user_id(client: "AsyncClient") -> None:
    response = await client.get(app.other_asgi_app.url_path_for("get_chat_list"))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "User not found"}


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
    assert response.json() == []


@pytest.mark.usefixtures("clear_db")
async def test_get_chat_list(client: "AsyncClient", user_db_f, chat_db_f, chat_relationship_db_f) -> None:
    user_uid = str(uuid.uuid4())
    await user_db_f.create(uid=user_uid)

    await generate_chat_history(user_uid, user_db_f, chat_db_f, chat_relationship_db_f, 5)

    user_2 = await user_db_f.create()
    await generate_chat_history(str(user_2.uid), user_db_f, chat_db_f, chat_relationship_db_f, 1)

    response = await client.get(
        app.other_asgi_app.url_path_for("get_chat_list"), headers={config.application.user_header_name: user_uid}
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 5
    for chat in response.json():
        assert len(chat["recipients"]) == 2
        assert user_uid in [recipient["user_uid"] for recipient in chat["recipients"]]
