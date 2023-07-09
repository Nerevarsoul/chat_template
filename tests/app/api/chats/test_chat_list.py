import uuid
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


@pytest.mark.usefixtures("clear_db")
async def test_get_unarchive_chat_list(client: "AsyncClient", user_db_f, chat_db_f, chat_relationship_db_f) -> None:
    user = await user_db_f.create()
    chat_1 = await chat_db_f.create()
    chat_2 = await chat_db_f.create()
    chat_3 = await chat_db_f.create()
    await chat_relationship_db_f.create(chat_id=chat_1.id, user_uid=user.uid)
    await chat_relationship_db_f.create(chat_id=chat_2.id, user_uid=user.uid)
    await chat_relationship_db_f.create(chat_id=chat_3.id, user_uid=user.uid, state=ChatState.ARCHIVE)
    active_chat_ids = [chat_1.id, chat_2.id]

    response = await client.get(
        app.other_asgi_app.url_path_for("get_chat_list"), headers={config.application.user_header_name: str(user.uid)}
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2

    for chat in response.json():
        assert chat["id"] in active_chat_ids
        assert str(user.uid) in [recipient["user_uid"] for recipient in chat["recipients"]]
        for recipient in chat["recipients"]:
            if recipient["user_uid"] == str(user.uid):
                assert recipient["state"] == ChatState.ACTIVE


@pytest.mark.usefixtures("clear_db")
async def test_get_archive_chat_list(client: "AsyncClient", user_db_f, chat_db_f, chat_relationship_db_f) -> None:
    user = await user_db_f.create()
    chat_1 = await chat_db_f.create()
    chat_2 = await chat_db_f.create()
    chat_3 = await chat_db_f.create()
    await chat_relationship_db_f.create(chat_id=chat_1.id, user_uid=user.uid, state=ChatState.ARCHIVE)
    await chat_relationship_db_f.create(chat_id=chat_2.id, user_uid=user.uid, state=ChatState.ARCHIVE)
    await chat_relationship_db_f.create(chat_id=chat_3.id, user_uid=user.uid)
    archived_chat_ids = [chat_1.id, chat_2.id]

    response = await client.get(
        app.other_asgi_app.url_path_for("get_chat_list"),
        headers={config.application.user_header_name: str(user.uid)},
        params={"from_archive": True},
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2

    for chat in response.json():
        assert chat["id"] in archived_chat_ids
        assert str(user.uid) in [recipient["user_uid"] for recipient in chat["recipients"]]
        for recipient in chat["recipients"]:
            if recipient["user_uid"] == str(user.uid):
                assert recipient["state"] == ChatState.ARCHIVE
