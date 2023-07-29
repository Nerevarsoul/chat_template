import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import pytest
from fastapi import status

from app import config
from app.db.enums import ChatState
from app.main import app
from tests.app.api.chats.utils import generate_chat_history

if TYPE_CHECKING:
    from httpx import AsyncClient


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
    user = await user_db_f.create()

    await generate_chat_history(user, chat_relationship_db_f, 5)

    user_2 = await user_db_f.create()
    await generate_chat_history(user_2, chat_relationship_db_f, 1)

    response = await client.get(
        app.other_asgi_app.url_path_for("get_chat_list"), headers={config.application.user_header_name: str(user.uid)}
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 5, response.json()
    for chat in response.json():
        assert len(chat["recipients"]) == 2
        assert str(user.uid) in [recipient["user_uid"] for recipient in chat["recipients"]]
        assert user.name in [recipient["user"]["name"] for recipient in chat["recipients"]]


@pytest.mark.usefixtures("clear_db")
async def test_get_chat_list_check_filter_archive(client: "AsyncClient", chat_relationship_db_f) -> None:
    chat_rel1 = await chat_relationship_db_f.create()
    user = chat_rel1.user
    chat_rel2 = await chat_relationship_db_f.create(user__uid=user.uid)
    await chat_relationship_db_f.create(user__uid=user.uid, state=ChatState.ARCHIVE)
    active_chat_ids = [chat_rel1.chat_id, chat_rel2.chat_id]

    response = await client.get(
        app.other_asgi_app.url_path_for("get_chat_list"), headers={config.application.user_header_name: str(user.uid)}
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2, response.json()

    for chat in response.json():
        assert chat["id"] in active_chat_ids
        assert str(user.uid) in [recipient["user_uid"] for recipient in chat["recipients"]]
        for recipient in chat["recipients"]:
            if recipient["user_uid"] == str(user.uid):
                assert recipient["state"] == ChatState.ACTIVE


@pytest.mark.usefixtures("clear_db")
async def test_get_archive_chat_list(client: "AsyncClient", chat_relationship_db_f) -> None:
    chat_rel1 = await chat_relationship_db_f.create(state=ChatState.ARCHIVE)
    user = chat_rel1.user
    chat_rel2 = await chat_relationship_db_f.create(user__uid=user.uid, state=ChatState.ARCHIVE)
    await chat_relationship_db_f.create(user__uid=user.uid)
    archived_chat_ids = [chat_rel1.chat_id, chat_rel2.chat_id]

    response = await client.get(
        app.other_asgi_app.url_path_for("get_chat_list"),
        headers={config.application.user_header_name: str(user.uid)},
        params={"from_archive": True},
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2, response.json()

    for chat in response.json():
        assert chat["id"] in archived_chat_ids
        assert str(user.uid) in [recipient["user_uid"] for recipient in chat["recipients"]]
        for recipient in chat["recipients"]:
            if recipient["user_uid"] == str(user.uid):
                assert recipient["state"] == ChatState.ARCHIVE


@pytest.mark.usefixtures("clear_db")
async def test_get_chat_list_with_pinned_chats(client: "AsyncClient", chat_relationship_db_f) -> None:
    chat_rel1 = await chat_relationship_db_f.create(time_pinned=datetime.utcnow())
    user = chat_rel1.user
    chat_rel2 = await chat_relationship_db_f.create(user__uid=user.uid)
    chat_rel3 = await chat_relationship_db_f.create(user__uid=user.uid, time_pinned=datetime.utcnow())
    expected_chat_list = [chat_rel1, chat_rel3, chat_rel2]

    response = await client.get(
        app.other_asgi_app.url_path_for("get_chat_list"),
        headers={config.application.user_header_name: str(user.uid)},
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 3, response.json()

    for chat, exp_chat in zip(response.json(), expected_chat_list):
        assert chat["id"] == exp_chat.chat_id
