from typing import TYPE_CHECKING

from fastapi import status
from sqlalchemy import func, select

from app.db.enums import ChatState, ChatUserRole
from app.db.models import Chat, ChatRelationship
from app.db.registry import registry
from app.main import app
from tests.factories.chats import CreateChatDataFactory

if TYPE_CHECKING:
    from httpx import AsyncClient


async def test_create_chat_without_chat_name(user_db_f, client: "AsyncClient") -> None:
    user1 = await user_db_f.create()
    user2 = await user_db_f.create()
    request_body = CreateChatDataFactory.build(
        factory_use_construct=True, chat_name=None, contacts=[user1.uid, user2.uid]
    )
    response = await client.post(app.other_asgi_app.url_path_for("create_chat"), content=request_body.json())
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async with registry.session() as session:
        query = select(func.count()).select_from(Chat)
        chats_quantity = (await session.execute(query)).scalar()
    assert chats_quantity == 0


async def test_create_chat_with_one_contact(user_db_f, client: "AsyncClient") -> None:
    user = await user_db_f.create()
    request_body = CreateChatDataFactory.build(factory_use_construct=True, contacts=[user.uid])
    response = await client.post(app.other_asgi_app.url_path_for("create_chat"), content=request_body.json())
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async with registry.session() as session:
        query = select(func.count()).select_from(Chat)
        chats_quantity = (await session.execute(query)).scalar()
    assert chats_quantity == 0


async def test_create_chat_with_identical_users(user_db_f, client: "AsyncClient") -> None:
    user = await user_db_f.create()
    request_body = CreateChatDataFactory.build(factory_use_construct=True, contacts=[user.uid, user.uid])
    response = await client.post(app.other_asgi_app.url_path_for("create_chat"), content=request_body.json())
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async with registry.session() as session:
        query = select(func.count()).select_from(Chat)
        chats_quantity = (await session.execute(query)).scalar()
    assert chats_quantity == 0


async def test_create_chat_with_unregistered_users(client: "AsyncClient") -> None:
    request_body = CreateChatDataFactory.build()
    response = await client.post(app.other_asgi_app.url_path_for("create_chat"), content=request_body.json())
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    async with registry.session() as session:
        query = select(func.count()).select_from(Chat)
        chats_quantity = (await session.execute(query)).scalar()
    assert chats_quantity == 0


async def test_create_chat(user_db_f, client: "AsyncClient") -> None:
    user1 = await user_db_f.create()
    user2 = await user_db_f.create()
    request_body = CreateChatDataFactory.build(contacts=[user1.uid, user2.uid])
    response = await client.post(app.other_asgi_app.url_path_for("create_chat"), content=request_body.json())
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["chat_name"] == request_body.chat_name
    assert set(response.json()["contacts"]) == set([str(contact_uuid) for contact_uuid in request_body.contacts])

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
