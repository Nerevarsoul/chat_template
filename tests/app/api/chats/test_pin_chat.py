from datetime import datetime
from typing import TYPE_CHECKING

import pytest
from fastapi import status
from sqlalchemy import select

from app import config
from app.db.enums import ChatState
from app.db.models import ChatRelationship
from app.db.registry import registry
from app.main import app
from tests.factories.schemas import SuccessfulChatApiResponseFactory

if TYPE_CHECKING:
    from httpx import AsyncClient


# Tests for pin_chat router


@pytest.mark.usefixtures("clear_db")
async def test_pin_chat_without_chat_id(user_db_f, client: "AsyncClient") -> None:
    user = await user_db_f.create()
    response = await client.post(
        app.other_asgi_app.url_path_for("pin_chat"),
        headers={config.application.user_header_name: str(user.uid)},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": {"chat_id": "Field required"}}


@pytest.mark.usefixtures("clear_db")
async def test_pin_chat_if_user_not_in_chat(client: "AsyncClient", user_db_f, chat_db_f) -> None:
    user = await user_db_f.create()
    chat = await chat_db_f.create()

    response = await client.post(
        app.other_asgi_app.url_path_for("pin_chat"),
        params={"chat_id": chat.id},
        headers={config.application.user_header_name: str(user.uid)},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.usefixtures("clear_db")
async def test_pin_chat_if_chat_already_pined(
    client: "AsyncClient",
    chat_relationship_db_f,
) -> None:
    chat_rel = await chat_relationship_db_f.create(time_pinned=datetime.utcnow())

    response_time = datetime.utcnow()
    response = await client.post(
        app.other_asgi_app.url_path_for("pin_chat"),
        params={"chat_id": chat_rel.chat_id},
        headers={config.application.user_header_name: str(chat_rel.user_uid)},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SuccessfulChatApiResponseFactory.build().model_dump()

    async with registry.session() as session:
        query = (
            select(ChatRelationship)
            .where(ChatRelationship.chat_id == chat_rel.chat_id)
            .where(ChatRelationship.user_uid == chat_rel.user_uid)
        )
        user_relationships = (await session.execute(query)).scalar()

    assert user_relationships.time_pinned > response_time
    assert user_relationships.time_pinned < datetime.utcnow()


@pytest.mark.usefixtures("clear_db")
async def test_pin_chat(client: "AsyncClient", chat_relationship_db_f) -> None:
    chat_rel = await chat_relationship_db_f.create()

    response_time = datetime.utcnow()
    response = await client.post(
        app.other_asgi_app.url_path_for("pin_chat"),
        headers={config.application.user_header_name: str(chat_rel.user_uid)},
        params={"chat_id": chat_rel.chat_id},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SuccessfulChatApiResponseFactory.build().model_dump()

    async with registry.session() as session:
        query = (
            select(ChatRelationship)
            .where(ChatRelationship.chat_id == chat_rel.chat_id)
            .where(ChatRelationship.user_uid == chat_rel.user_uid)
        )
        user_relationships = (await session.execute(query)).scalar()

    assert user_relationships.time_pinned > response_time
    assert user_relationships.time_pinned < datetime.utcnow()


# Tests for unpin_chat router


@pytest.mark.usefixtures("clear_db")
async def test_unpin_chat_without_chat_id(user_db_f, client: "AsyncClient") -> None:
    user = await user_db_f.create()
    response = await client.post(
        app.other_asgi_app.url_path_for("unpin_chat"),
        headers={config.application.user_header_name: str(user.uid)},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": {"chat_id": "Field required"}}


@pytest.mark.usefixtures("clear_db")
async def test_unpin_chat_if_user_not_in_chat(client: "AsyncClient", user_db_f, chat_db_f) -> None:
    user = await user_db_f.create()
    chat = await chat_db_f.create()

    response = await client.post(
        app.other_asgi_app.url_path_for("unpin_chat"),
        params={"chat_id": chat.id},
        headers={config.application.user_header_name: str(user.uid)},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.usefixtures("clear_db")
async def test_unpin_chat_if_chat_not_pined(client: "AsyncClient", chat_relationship_db_f) -> None:
    chat_rel = await chat_relationship_db_f.create()

    response = await client.post(
        app.other_asgi_app.url_path_for("unpin_chat"),
        params={"chat_id": chat_rel.chat_id},
        headers={config.application.user_header_name: str(chat_rel.user_uid)},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SuccessfulChatApiResponseFactory.build().model_dump()

    async with registry.session() as session:
        query = (
            select(ChatRelationship)
            .where(ChatRelationship.chat_id == chat_rel.chat_id)
            .where(ChatRelationship.user_uid == chat_rel.user_uid)
        )
        user_relationships = (await session.execute(query)).scalar()

    assert user_relationships.time_pinned is None


@pytest.mark.usefixtures("clear_db")
async def test_unpin_chat(client: "AsyncClient", user_db_f, chat_relationship_db_f, chat_db_f) -> None:
    chat_rel = await chat_relationship_db_f.create(time_pinned=datetime.utcnow())

    response = await client.post(
        app.other_asgi_app.url_path_for("unpin_chat"),
        headers={config.application.user_header_name: str(chat_rel.user_uid)},
        params={"chat_id": chat_rel.chat_id},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == SuccessfulChatApiResponseFactory.build().model_dump()

    async with registry.session() as session:
        query = (
            select(ChatRelationship)
            .where(ChatRelationship.chat_id == chat_rel.chat_id)
            .where(ChatRelationship.user_uid == chat_rel.user_uid)
        )
        user_relationships = (await session.execute(query)).scalar()

    assert user_relationships.time_pinned is None
