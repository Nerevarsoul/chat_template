from typing import TYPE_CHECKING

import pytest
from fastapi import status
from sqlalchemy import select

from app import config
from app.db.enums import ChatState
from app.db.models import ChatRelationship
from app.db.registry import registry
from app.main import app

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.usefixtures("clear_db")
async def test_archive_chat_without_chat_id(user_db_f, client: "AsyncClient") -> None:
    user = await user_db_f.create()
    response = await client.post(
        app.other_asgi_app.url_path_for("archive_chat"),
        headers={config.application.user_header_name: str(user.uid)},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": {"chat_id": "field required"}}


@pytest.mark.usefixtures("clear_db")
async def test_archive_chat_if_user_not_in_chat(client: "AsyncClient", user_db_f, chat_db_f) -> None:
    user = await user_db_f.create()
    chat = await chat_db_f.create()

    response = await client.post(
        app.other_asgi_app.url_path_for("archive_chat"),
        params={"chat_id": chat.id},
        headers={config.application.user_header_name: str(user.uid)},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.usefixtures("clear_db")
async def test_archive_chat_if_chat_already_archived(
    client: "AsyncClient", user_db_f, chat_relationship_db_f, chat_db_f
) -> None:
    user = await user_db_f.create()
    chat = await chat_db_f.create()
    await chat_relationship_db_f.create(chat_id=chat.id, user_uid=user.uid, state=ChatState.ARCHIVE)

    response = await client.post(
        app.other_asgi_app.url_path_for("archive_chat"),
        params={"chat_id": chat.id},
        headers={config.application.user_header_name: str(user.uid)},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": {"chat_id": "chat is already archived"}}


@pytest.mark.usefixtures("clear_db")
async def test_archive_chat(client: "AsyncClient", user_db_f, chat_relationship_db_f, chat_db_f) -> None:
    user = await user_db_f.create()
    chat = await chat_db_f.create()
    await chat_relationship_db_f.create(chat_id=chat.id, user_uid=user.uid)

    response = await client.post(
        app.other_asgi_app.url_path_for("archive_chat"),
        headers={config.application.user_header_name: str(user.uid)},
        params={"chat_id": chat.id},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"result": {"success": True}}

    async with registry.session() as session:
        query = (
            select(ChatRelationship)
            .where(ChatRelationship.chat_id == chat.id)
            .where(ChatRelationship.user_uid == user.uid)
        )
        user_relationships = (await session.execute(query)).scalar()

    assert user_relationships.state == ChatState.ARCHIVE
