from random import choice, randint
from typing import TYPE_CHECKING

import pytest
from fastapi import status

from app import config
from app.db.enums import ChatUserRole
from app.main import app
from tests.app.api.chats.utils import get_sorted_messages_id_list

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.usefixtures("clear_db")
async def test_get_message_history_if_user_not_in_chat(
    client: "AsyncClient", user_db_f, chat_relationship_db_f, message_db_f
) -> None:
    user_1 = await user_db_f.create()
    chat_rel = await chat_relationship_db_f.create(user_role=ChatUserRole.CREATOR)
    await message_db_f.create(user_uid=chat_rel.user_uid, chat_id=chat_rel.chat_id)

    response = await client.get(
        app.other_asgi_app.url_path_for("get_message_history"),
        headers={config.application.user_header_name: str(user_1.uid)},
        params={"chat_id": chat_rel.chat_id},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


@pytest.mark.usefixtures("clear_db")
async def test_get_message_history(client: "AsyncClient", chat_relationship_db_f, message_db_f) -> None:
    chat_rel = await chat_relationship_db_f.create(user_role=ChatUserRole.CREATOR)
    messages_count = randint(5, 15)
    messages_id_list = await get_sorted_messages_id_list(
        messages_count, chat_rel.user_uid, chat_rel.chat_id, message_db_f
    )

    response = await client.get(
        app.other_asgi_app.url_path_for("get_message_history"),
        headers={config.application.user_header_name: str(chat_rel.user_uid)},
        params={"chat_id": chat_rel.chat_id},
    )

    message_history = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(message_history) == messages_count

    for message, message_id in zip(message_history, messages_id_list):
        print(message["id"], message_id)
        assert message["user_uid"] == str(chat_rel.user_uid)
        assert message["chat_id"] == chat_rel.chat_id
        assert message["id"] == message_id


@pytest.mark.usefixtures("clear_db")
async def test_get_message_history_with_default_page_size_param(
    client: "AsyncClient", chat_relationship_db_f, message_db_f
) -> None:
    chat_rel = await chat_relationship_db_f.create(user_role=ChatUserRole.CREATOR)
    messages_count = config.application.message_history_page_size + 10
    messages_id_list = await get_sorted_messages_id_list(
        messages_count, chat_rel.user_uid, chat_rel.chat_id, message_db_f
    )

    response = await client.get(
        app.other_asgi_app.url_path_for("get_message_history"),
        headers={config.application.user_header_name: str(chat_rel.user_uid)},
        params={"chat_id": chat_rel.chat_id},
    )

    message_history = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(message_history) == config.application.message_history_page_size

    for message, message_id in zip(message_history, messages_id_list):
        assert message["user_uid"] == str(chat_rel.user_uid)
        assert message["chat_id"] == chat_rel.chat_id
        assert message["id"] == message_id


@pytest.mark.usefixtures("clear_db")
async def test_get_message_history_with_page_size_param(
    client: "AsyncClient", chat_relationship_db_f, message_db_f
) -> None:
    chat_rel = await chat_relationship_db_f.create(user_role=ChatUserRole.CREATOR)
    messages_count = 20
    page_size = randint(5, 15)
    messages_id_list = await get_sorted_messages_id_list(
        messages_count, chat_rel.user_uid, chat_rel.chat_id, message_db_f
    )

    response = await client.get(
        app.other_asgi_app.url_path_for("get_message_history"),
        headers={config.application.user_header_name: str(chat_rel.user_uid)},
        params={"chat_id": chat_rel.chat_id, "page_size": page_size},
    )

    message_history = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(message_history) == page_size

    for message, message_id in zip(message_history, messages_id_list):
        assert message["user_uid"] == str(chat_rel.user_uid)
        assert message["chat_id"] == chat_rel.chat_id
        assert message["id"] == message_id


@pytest.mark.usefixtures("clear_db")
async def test_get_message_history_with_message_id_param(
    client: "AsyncClient", chat_relationship_db_f, message_db_f
) -> None:
    chat_rel = await chat_relationship_db_f.create(user_role=ChatUserRole.CREATOR)
    messages_count = config.application.message_history_page_size * 2
    messages_id_list = await get_sorted_messages_id_list(
        messages_count, chat_rel.user_uid, chat_rel.chat_id, message_db_f
    )
    message_index = config.application.message_history_page_size
    message_id = messages_id_list[message_index]

    response = await client.get(
        app.other_asgi_app.url_path_for("get_message_history"),
        headers={config.application.user_header_name: str(chat_rel.user_uid)},
        params={"chat_id": chat_rel.chat_id, "message_id": message_id},
    )

    message_history = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(message_history) == config.application.message_history_page_size

    for message, message_id in zip(message_history, messages_id_list[message_index:]):
        assert message["user_uid"] == str(chat_rel.user_uid)
        assert message["chat_id"] == chat_rel.chat_id
        assert message["id"] == message_id
