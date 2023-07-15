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
    client: "AsyncClient", user_db_f, chat_relationship_db_f
) -> None:
    user_1 = await user_db_f.create()
    chat_rel = await chat_relationship_db_f.create(user_role=ChatUserRole.CREATOR)
    await chat_relationship_db_f.create(chat__id=chat_rel.chat_id)

    response = await client.get(
        app.other_asgi_app.url_path_for("get_chat_recipients"),
        headers={config.application.user_header_name: str(user_1.uid)},
        params={"chat_id": chat_rel.chat_id},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.usefixtures("clear_db")
async def test_get_chat_recipients(client: "AsyncClient", chat_relationship_db_f) -> None:
    chat_rel_1 = await chat_relationship_db_f.create(user_role=ChatUserRole.CREATOR)
    chat_rel_2 = await chat_relationship_db_f.create(chat__id=chat_rel_1.chat_id)

    response = await client.get(
        app.other_asgi_app.url_path_for("get_chat_recipients"),
        headers={config.application.user_header_name: str(chat_rel_1.user_uid)},
        params={"chat_id": chat_rel_1.chat_id},
    )
    chat_recipients = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(chat_recipients) == 2, chat_recipients
    for recipient in chat_recipients:
        if recipient["user_uid"] == str(chat_rel_1.user_uid):
            assert recipient["state"] == ChatState.ACTIVE
            assert recipient["user_role"] == ChatUserRole.CREATOR
        else:
            assert recipient["user_uid"] == str(chat_rel_2.user_uid)
            assert recipient["state"] == ChatState.ACTIVE
            assert recipient["user_role"] == ChatUserRole.USER


@pytest.mark.usefixtures("clear_db")
async def test_get_chat_recipients_from_non_existent_chat(client: "AsyncClient", user_db_f) -> None:
    user_1 = await user_db_f.create()

    response = await client.get(
        app.other_asgi_app.url_path_for("get_chat_recipients"),
        headers={config.application.user_header_name: str(user_1.uid)},
        params={"chat_id": 1},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.usefixtures("clear_db")
async def test_get_chat_recipients_if_deleted_recipients_exist(client: "AsyncClient", chat_relationship_db_f) -> None:
    chat_rel = await chat_relationship_db_f.create(user_role=ChatUserRole.CREATOR)
    await chat_relationship_db_f.create(chat__id=chat_rel.chat_id)
    await chat_relationship_db_f.create(chat__id=chat_rel.chat_id, state=ChatState.DELETED)

    response = await client.get(
        app.other_asgi_app.url_path_for("get_chat_recipients"),
        headers={config.application.user_header_name: str(chat_rel.user_uid)},
        params={"chat_id": chat_rel.chat_id},
    )
    chat_recipients = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert len(chat_recipients) == 2, chat_recipients
