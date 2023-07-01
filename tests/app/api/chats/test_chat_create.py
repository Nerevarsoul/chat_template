from typing import TYPE_CHECKING

import pytest
from fastapi import status
from sqlalchemy import func, select

from app import config
from app.db.enums import ChatState, ChatUserRole
from app.db.models import Chat, ChatRelationship
from app.db.registry import registry
from app.main import app
from tests.factories.schemas import CreateChatDataFactory

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.usefixtures("clear_db")
async def test_create_chat_without_chat_name(user_db_f, client: "AsyncClient") -> None:
    user1 = await user_db_f.create()
    user2 = await user_db_f.create()
    request_body = CreateChatDataFactory.build(
        factory_use_construct=True, chat_name="", contacts=[user1.uid, user2.uid]
    )
    response = await client.post(
        app.other_asgi_app.url_path_for("create_chat"),
        content=request_body.json(),
        headers={config.application.user_header_name: str(user1.uid)},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": {"chat_name": "chat name must contain characters"}}

    async with registry.session() as session:
        query = select(func.count()).select_from(Chat)
        chats_quantity = (await session.execute(query)).scalar()
    assert chats_quantity == 0


@pytest.mark.usefixtures("clear_db")
async def test_create_chat_with_chat_name_is_none(user_db_f, client: "AsyncClient") -> None:
    user1 = await user_db_f.create()
    user2 = await user_db_f.create()
    request_body = CreateChatDataFactory.build(
        factory_use_construct=True, chat_name=None, contacts=[user1.uid, user2.uid]
    )
    response = await client.post(
        app.other_asgi_app.url_path_for("create_chat"),
        content=request_body.json(),
        headers={config.application.user_header_name: str(user1.uid)},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": {"chat_name": "none is not an allowed value"}}

    async with registry.session() as session:
        query = select(func.count()).select_from(Chat)
        chats_quantity = (await session.execute(query)).scalar()
    assert chats_quantity == 0


@pytest.mark.usefixtures("clear_db")
async def test_create_chat_without_contacts_list(user_db_f, client: "AsyncClient") -> None:
    user = await user_db_f.create()
    request_body = CreateChatDataFactory.build(factory_use_construct=True, contacts=[])
    response = await client.post(
        app.other_asgi_app.url_path_for("create_chat"),
        content=request_body.json(),
        headers={config.application.user_header_name: str(user.uid)},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": {"contacts": "chat cannot be created with one user"}}

    async with registry.session() as session:
        query = select(func.count()).select_from(Chat)
        chats_quantity = (await session.execute(query)).scalar()
    assert chats_quantity == 0


@pytest.mark.usefixtures("clear_db")
async def test_create_chat_with_one_contact(user_db_f, client: "AsyncClient") -> None:
    user = await user_db_f.create()
    request_body = CreateChatDataFactory.build(contacts=[user.uid])
    response = await client.post(
        app.other_asgi_app.url_path_for("create_chat"),
        content=request_body.json(),
        headers={config.application.user_header_name: str(user.uid)},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": {"contacts": "chat cannot be created with one user"}}

    async with registry.session() as session:
        query = select(func.count()).select_from(Chat)
        chats_quantity = (await session.execute(query)).scalar()
    assert chats_quantity == 0


@pytest.mark.usefixtures("clear_db")
async def test_create_chat_with_identical_users(user_db_f, client: "AsyncClient") -> None:
    user1 = await user_db_f.create()
    user2 = await user_db_f.create()
    request_body = CreateChatDataFactory.build(factory_use_construct=True, contacts=[user2.uid, user2.uid])
    response = await client.post(
        app.other_asgi_app.url_path_for("create_chat"),
        content=request_body.json(),
        headers={config.application.user_header_name: str(user1.uid)},
    )
    assert response.status_code == status.HTTP_201_CREATED

    async with registry.session() as session:
        query = (
            select(func.count())
            .select_from(ChatRelationship)
            .where(ChatRelationship.chat_id == response.json()["chat_id"])
        )
        chats_reletionship_quantity = (await session.execute(query)).scalar()
    assert chats_reletionship_quantity == 2


@pytest.mark.usefixtures("clear_db")
async def test_create_chat(user_db_f, client: "AsyncClient") -> None:
    user1 = await user_db_f.create()
    user2 = await user_db_f.create()
    request_body = CreateChatDataFactory.build(contacts=[user2.uid])
    response = await client.post(
        app.other_asgi_app.url_path_for("create_chat"),
        content=request_body.json(),
        headers={config.application.user_header_name: str(user1.uid)},
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["chat_name"] == request_body.chat_name
    assert set(response.json()["contacts"]) == set([str(user1.uid), str(user2.uid)])

    async with registry.session() as session:
        query = select(Chat).where(Chat.id == response.json()["chat_id"])
        created_chat = (await session.execute(query)).scalar()

        query = (
            select(ChatRelationship)
            .where(ChatRelationship.chat_id == created_chat.id)
            .where(ChatRelationship.user_uid == user1.uid)
        )
        chat_creator_relationships = (await session.execute(query)).scalar()

        query = (
            select(ChatRelationship)
            .where(ChatRelationship.chat_id == created_chat.id)
            .where(ChatRelationship.user_uid == user2.uid)
        )
        user_relationships = (await session.execute(query)).scalar()
    assert created_chat.state == ChatState.ACTIVE
    assert chat_creator_relationships.user_role == ChatUserRole.CREATOR
    assert user_relationships.user_role == ChatUserRole.USER
