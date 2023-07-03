import uuid
from typing import TYPE_CHECKING

import pytest
from fastapi import status
from sqlalchemy import func, select

from app import config
from app.db.enums import ChatState, ChatUserRole
from app.db.models import ChatRelationship
from app.db.registry import registry
from app.main import app

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.usefixtures("clear_db")
async def test_add_recipients_without_chat_id(user_db_f, client: "AsyncClient") -> None:
    user_1 = await user_db_f.create()
    user_2 = await user_db_f.create()
    response = await client.post(
        app.other_asgi_app.url_path_for("add_recipients"),
        json={"contacts": [str(user_2.uid)]},
        headers={config.application.user_header_name: str(user_1.uid)},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": {"chat_id": "field required"}}


@pytest.mark.usefixtures("clear_db")
async def test_add_recipients_without_contacts(user_db_f, chat_db_f, client: "AsyncClient") -> None:
    user = await user_db_f.create()
    chat = await chat_db_f.create()
    response = await client.post(
        app.other_asgi_app.url_path_for("add_recipients"),
        json={"chat_id": chat.id},
        headers={config.application.user_header_name: str(user.uid)},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": {"contacts": "field required"}}


@pytest.mark.usefixtures("clear_db")
async def test_add_recipients_if_user_not_in_chat(
    client: "AsyncClient", user_db_f, chat_relationship_db_f, chat_db_f
) -> None:
    user_1 = await user_db_f.create()
    user_2 = await user_db_f.create()
    user_3 = await user_db_f.create()
    chat = await chat_db_f.create()
    await chat_relationship_db_f.create(chat_id=chat.id, user_uid=user_1.uid, user_role=ChatUserRole.CREATOR)

    response = await client.post(
        app.other_asgi_app.url_path_for("add_recipients"),
        headers={config.application.user_header_name: str(user_2.uid)},
        json={"chat_id": chat.id, "contacts": [str(user_3.uid)]},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.usefixtures("clear_db")
async def test_add_recipients_if_contacts_already_in_chat(
    client: "AsyncClient", user_db_f, chat_relationship_db_f, chat_db_f
) -> None:
    user_1 = await user_db_f.create()
    user_2 = await user_db_f.create()
    chat = await chat_db_f.create()
    await chat_relationship_db_f.create(chat_id=chat.id, user_uid=user_1.uid, user_role=ChatUserRole.CREATOR)
    await chat_relationship_db_f.create(chat_id=chat.id, user_uid=user_2.uid)

    response = await client.post(
        app.other_asgi_app.url_path_for("add_recipients"),
        headers={config.application.user_header_name: str(user_1.uid)},
        json={"chat_id": chat.id, "contacts": [str(user_2.uid)]},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": {"contacts": "all contacts already in chat"}}

    async with registry.session() as session:
        query = select(func.count()).select_from(ChatRelationship).where(ChatRelationship.chat_id == chat.id)
        chats_reletionship_quantity = (await session.execute(query)).scalar()
    assert chats_reletionship_quantity == 2


@pytest.mark.usefixtures("clear_db")
async def test_add_recipients_if_one_of_contacts_already_in_chat(
    client: "AsyncClient", user_db_f, chat_relationship_db_f, chat_db_f
) -> None:
    user_1 = await user_db_f.create()
    user_2 = await user_db_f.create()
    user_3 = await user_db_f.create()
    chat = await chat_db_f.create()
    await chat_relationship_db_f.create(chat_id=chat.id, user_uid=user_1.uid, user_role=ChatUserRole.CREATOR)
    await chat_relationship_db_f.create(chat_id=chat.id, user_uid=user_2.uid)

    response = await client.post(
        app.other_asgi_app.url_path_for("add_recipients"),
        headers={config.application.user_header_name: str(user_1.uid)},
        json={"chat_id": chat.id, "contacts": [str(user_3.uid)]},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"result": {"success": True}}

    async with registry.session() as session:
        query = select(func.count()).select_from(ChatRelationship).where(ChatRelationship.chat_id == chat.id)
        chats_reletionship_quantity = (await session.execute(query)).scalar()
    assert chats_reletionship_quantity == 3


@pytest.mark.usefixtures("clear_db")
async def test_add_recipients(client: "AsyncClient", user_db_f, chat_relationship_db_f, chat_db_f) -> None:
    user_1 = await user_db_f.create()
    user_2 = await user_db_f.create()
    user_3 = await user_db_f.create()
    chat = await chat_db_f.create()
    await chat_relationship_db_f.create(chat_id=chat.id, user_uid=user_1.uid, user_role=ChatUserRole.CREATOR)

    response = await client.post(
        app.other_asgi_app.url_path_for("add_recipients"),
        headers={config.application.user_header_name: str(user_1.uid)},
        json={"chat_id": chat.id, "contacts": [str(user_2.uid), str(user_3.uid)]},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"result": {"success": True}}

    async with registry.session() as session:
        query = select(func.count()).select_from(ChatRelationship).where(ChatRelationship.chat_id == chat.id)
        chats_reletionship_quantity = (await session.execute(query)).scalar()
    assert chats_reletionship_quantity == 3

    async with registry.session() as session:
        query = (
            select(ChatRelationship)
            .where(ChatRelationship.chat_id == chat.id)
            .where(ChatRelationship.user_uid == user_2.uid)
        )
        user_2_relationships = (await session.execute(query)).scalar()

        query = (
            select(ChatRelationship)
            .where(ChatRelationship.chat_id == chat.id)
            .where(ChatRelationship.user_uid == user_3.uid)
        )
        user_3_relationships = (await session.execute(query)).scalar()

    assert user_2_relationships.state == ChatState.ACTIVE
    assert user_2_relationships.user_role == ChatUserRole.USER
    assert user_3_relationships.state == ChatState.ACTIVE
    assert user_3_relationships.user_role == ChatUserRole.USER


@pytest.mark.usefixtures("clear_db")
async def test_add_not_exist_recipients(client: "AsyncClient", user_db_f, chat_relationship_db_f, chat_db_f) -> None:
    user_1 = await user_db_f.create()
    user_2_uid = uuid.uuid4()
    chat = await chat_db_f.create()
    await chat_relationship_db_f.create(chat_id=chat.id, user_uid=user_1.uid, user_role=ChatUserRole.CREATOR)

    response = await client.post(
        app.other_asgi_app.url_path_for("add_recipients"),
        headers={config.application.user_header_name: str(user_1.uid)},
        json={"chat_id": chat.id, "contacts": [str(user_2_uid)]},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": {"contacts": "one of contacts is not exist"}}


@pytest.mark.usefixtures("clear_db")
async def test_add_recipients_to_not_exist_chat(client: "AsyncClient", user_db_f) -> None:
    user_1 = await user_db_f.create()
    user_2 = await user_db_f.create()

    response = await client.post(
        app.other_asgi_app.url_path_for("add_recipients"),
        headers={config.application.user_header_name: str(user_1.uid)},
        json={"chat_id": 1, "contacts": [str(user_2.uid)]},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
