from typing import TYPE_CHECKING

import pytest
from fastapi import status

from app import config
from app.db.enums import ChatState, ChatUserRole
from app.main import app

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.usefixtures("clear_db")
async def test_get_chat_recipients_if_user_not_in_chat(
    client: "AsyncClient", user_db_f, chat_relationship_db_f, chat_db_f
) -> None:
    user_1 = await user_db_f.create()
    user_2 = await user_db_f.create()
    user_3 = await user_db_f.create()
    chat = await chat_db_f.create()
    await chat_relationship_db_f.create(chat_id=chat.id, user_uid=user_1.uid, user_role=ChatUserRole.CREATOR)
    await chat_relationship_db_f.create(chat_id=chat.id, user_uid=user_2.uid)

    response = await client.get(
        app.other_asgi_app.url_path_for("get_chat_recipients"),
        headers={config.application.user_header_name: str(user_3.uid)},
        params={"chat_id": chat.id},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.usefixtures("clear_db")
async def test_get_chat_recipients(client: "AsyncClient", user_db_f, chat_relationship_db_f, chat_db_f) -> None:
    user_1 = await user_db_f.create()
    user_2 = await user_db_f.create()
    chat = await chat_db_f.create()
    await chat_relationship_db_f.create(chat_id=chat.id, user_uid=user_1.uid, user_role=ChatUserRole.CREATOR)
    await chat_relationship_db_f.create(chat_id=chat.id, user_uid=user_2.uid)

    response = await client.get(
        app.other_asgi_app.url_path_for("get_chat_recipients"),
        headers={config.application.user_header_name: str(user_1.uid)},
        params={"chat_id": chat.id},
    )
    chat_recipients = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(chat_recipients) == 2
    for recipient in chat_recipients:
        if recipient["user_uid"] == str(user_1.uid):
            assert recipient["state"] == ChatState.ACTIVE
            assert recipient["user_role"] == ChatUserRole.CREATOR
        else:
            assert recipient["user_uid"] == str(user_2.uid)
            assert recipient["state"] == ChatState.ACTIVE
            assert recipient["user_role"] == ChatUserRole.USER


@pytest.mark.usefixtures("clear_db")
async def test_get_chat_recipients_from_non_existent_chat(
    client: "AsyncClient", user_db_f, chat_relationship_db_f, chat_db_f
) -> None:
    user_1 = await user_db_f.create()

    response = await client.get(
        app.other_asgi_app.url_path_for("get_chat_recipients"),
        headers={config.application.user_header_name: str(user_1.uid)},
        params={"chat_id": 1},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
