from typing import TYPE_CHECKING

from fastapi import status

from app.api.chats.schemas import CreateChatData, CreateChatResponse
from app.main import app

if TYPE_CHECKING:
    from httpx import AsyncClient


async def test_create_chat(user_db_f, client: "AsyncClient") -> None:
    user1 = await user_db_f.create()
    user2 = await user_db_f.create()
    chat_name = "chat_name"
    request_body = CreateChatData(chat_name=chat_name, contacts=[user1.uid, user2.uid]).json()
    response = await client.post(app.other_asgi_app.url_path_for("create_chat"), content=request_body)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {"chat_id": 1, "chat_name": chat_name, "contacts": [str(user1.uid), str(user2.uid)]}
