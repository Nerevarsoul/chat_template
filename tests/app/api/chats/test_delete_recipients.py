import uuid
from typing import TYPE_CHECKING

import pytest
from fastapi import status
from sqlalchemy import and_, func, select

from app import config
from app.db.enums import ChatState, ChatUserRole
from app.db.models import ChatRelationship
from app.db.registry import registry
from app.main import app

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.usefixtures("clear_db")
async def test_delete_recipients_without_chat_id(user_db_f, client: "AsyncClient") -> None:
    user_1 = await user_db_f.create()
    user_2 = await user_db_f.create()
    response = await client.post(
        app.other_asgi_app.url_path_for("delete_recipients"),
        json={"contacts": [str(user_2.uid)]},
        headers={config.application.user_header_name: str(user_1.uid)},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": {"chat_id": "Field required"}}


@pytest.mark.usefixtures("clear_db")
async def test_delete_recipients_without_contacts(user_db_f, chat_db_f, client: "AsyncClient") -> None:
    user = await user_db_f.create()
    chat = await chat_db_f.create()
    response = await client.post(
        app.other_asgi_app.url_path_for("delete_recipients"),
        json={"chat_id": chat.id},
        headers={config.application.user_header_name: str(user.uid)},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": {"contacts": "Field required"}}


@pytest.mark.usefixtures("clear_db")
async def test_delete_recipients_if_user_not_in_chat(client: "AsyncClient", user_db_f, chat_relationship_db_f) -> None:
    user = await user_db_f.create()
    chat_rel = await chat_relationship_db_f.create()
    await chat_relationship_db_f.create(chat__id=chat_rel.chat_id, user_role=ChatUserRole.CREATOR)

    response = await client.post(
        app.other_asgi_app.url_path_for("delete_recipients"),
        headers={config.application.user_header_name: str(user.uid)},
        json={"chat_id": chat_rel.chat_id, "contacts": [str(chat_rel.user_uid)]},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.usefixtures("clear_db")
async def test_delete_recipients_if_contacts_not_in_chat(
    client: "AsyncClient", user_db_f, chat_relationship_db_f
) -> None:
    user = await user_db_f.create()
    chat_rel = await chat_relationship_db_f.create(user_role=ChatUserRole.CREATOR)
    await chat_relationship_db_f.create(chat__id=chat_rel.chat_id)

    response = await client.post(
        app.other_asgi_app.url_path_for("delete_recipients"),
        headers={config.application.user_header_name: str(chat_rel.user_uid)},
        json={"chat_id": chat_rel.chat_id, "contacts": [str(user.uid)]},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": {"contacts": "all contacts not in chat"}}

    async with registry.session() as session:
        query = select(func.count()).select_from(ChatRelationship).where(ChatRelationship.chat_id == chat_rel.chat_id)
        chats_reletionship_quantity = (await session.execute(query)).scalar()
    assert chats_reletionship_quantity == 2


@pytest.mark.usefixtures("clear_db")
async def test_delete_recipients_if_one_of_contacts_not_in_chat(
    client: "AsyncClient", user_db_f, chat_relationship_db_f
) -> None:
    user = await user_db_f.create()
    chat_rel_1 = await chat_relationship_db_f.create(user_role=ChatUserRole.CREATOR)
    chat_rel_2 = await chat_relationship_db_f.create(chat__id=chat_rel_1.chat_id)
    await chat_relationship_db_f.create(chat__id=chat_rel_1.chat_id)

    response = await client.post(
        app.other_asgi_app.url_path_for("delete_recipients"),
        headers={config.application.user_header_name: str(chat_rel_1.user_uid)},
        json={"chat_id": chat_rel_1.chat_id, "contacts": [str(user.uid), str(chat_rel_2.user_uid)]},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"result": {"success": True}}

    async with registry.session() as session:
        query = (
            select(func.count())
            .select_from(ChatRelationship)
            .where(and_(ChatRelationship.chat_id == chat_rel_1.chat_id, ChatRelationship.state != ChatState.DELETED))
        )
        chats_reletionship_quantity = (await session.execute(query)).scalar()

    assert chats_reletionship_quantity == 2


@pytest.mark.usefixtures("clear_db")
async def test_delete_all_recipients_except_one(client: "AsyncClient", chat_relationship_db_f) -> None:
    chat_rel_1 = await chat_relationship_db_f.create(user_role=ChatUserRole.CREATOR)
    chat_rel_2 = await chat_relationship_db_f.create(chat__id=chat_rel_1.chat_id)

    response = await client.post(
        app.other_asgi_app.url_path_for("delete_recipients"),
        headers={config.application.user_header_name: str(chat_rel_1.user_uid)},
        json={"chat_id": chat_rel_1.chat_id, "contacts": [str(chat_rel_2.user_uid)]},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": {"contacts": "only one user will remain in the chat"}}

    async with registry.session() as session:
        query = (
            select(func.count())
            .select_from(ChatRelationship)
            .where(and_(ChatRelationship.chat_id == chat_rel_1.chat_id, ChatRelationship.state != ChatState.DELETED))
        )
        chats_reletionship_quantity = (await session.execute(query)).scalar()
    assert chats_reletionship_quantity == 2


@pytest.mark.usefixtures("clear_db")
async def test_delete_all_recipients(client: "AsyncClient", chat_relationship_db_f) -> None:
    chat_rel_1 = await chat_relationship_db_f.create(user_role=ChatUserRole.CREATOR)
    chat_rel_2 = await chat_relationship_db_f.create(chat__id=chat_rel_1.chat_id)

    response = await client.post(
        app.other_asgi_app.url_path_for("delete_recipients"),
        headers={config.application.user_header_name: str(chat_rel_1.user_uid)},
        json={"chat_id": chat_rel_1.chat_id, "contacts": [str(chat_rel_1.user_uid), str(chat_rel_2.user_uid)]},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": {"contacts": "only one user will remain in the chat"}}

    async with registry.session() as session:
        query = (
            select(func.count())
            .select_from(ChatRelationship)
            .where(and_(ChatRelationship.chat_id == chat_rel_1.chat_id, ChatRelationship.state != ChatState.DELETED))
        )
        chats_reletionship_quantity = (await session.execute(query)).scalar()
    assert chats_reletionship_quantity == 2


@pytest.mark.usefixtures("clear_db")
async def test_delete_recipients(client: "AsyncClient", chat_relationship_db_f) -> None:
    chat_rel_1 = await chat_relationship_db_f.create(user_role=ChatUserRole.CREATOR)
    chat_rel_2 = await chat_relationship_db_f.create(chat__id=chat_rel_1.chat_id)
    chat_rel_3 = await chat_relationship_db_f.create(chat__id=chat_rel_1.chat_id)

    response = await client.post(
        app.other_asgi_app.url_path_for("delete_recipients"),
        headers={config.application.user_header_name: str(chat_rel_1.user_uid)},
        json={"chat_id": chat_rel_1.chat_id, "contacts": [str(chat_rel_3.user_uid)]},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"result": {"success": True}}

    async with registry.session() as session:
        query = (
            select(func.count())
            .select_from(ChatRelationship)
            .where(and_(ChatRelationship.chat_id == chat_rel_1.chat_id, ChatRelationship.state != ChatState.DELETED))
        )
        chats_reletionship_quantity = (await session.execute(query)).scalar()
    assert chats_reletionship_quantity == 2

    async with registry.session() as session:
        query = (
            select(ChatRelationship)
            .where(ChatRelationship.chat_id == chat_rel_1.chat_id)
            .where(ChatRelationship.user_uid == chat_rel_1.user_uid)
        )
        user_1_relationships = (await session.execute(query)).scalar()

        query = (
            select(ChatRelationship)
            .where(ChatRelationship.chat_id == chat_rel_1.chat_id)
            .where(ChatRelationship.user_uid == chat_rel_2.user_uid)
        )
        user_2_relationships = (await session.execute(query)).scalar()

        query = (
            select(ChatRelationship)
            .where(ChatRelationship.chat_id == chat_rel_1.chat_id)
            .where(ChatRelationship.user_uid == chat_rel_3.user_uid)
        )
        user_3_relationships = (await session.execute(query)).scalar()

    assert user_1_relationships.state == ChatState.ACTIVE
    assert user_2_relationships.state == ChatState.ACTIVE
    assert user_3_relationships.state == ChatState.DELETED


@pytest.mark.usefixtures("clear_db")
async def test_delete_not_exist_recipients(client: "AsyncClient", chat_relationship_db_f) -> None:
    chat_rel = await chat_relationship_db_f.create(user_role=ChatUserRole.CREATOR)

    response = await client.post(
        app.other_asgi_app.url_path_for("delete_recipients"),
        headers={config.application.user_header_name: str(chat_rel.user_uid)},
        json={"chat_id": chat_rel.chat_id, "contacts": [str(uuid.uuid4())]},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": {"contacts": "all contacts not in chat"}}
