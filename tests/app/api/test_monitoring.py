from typing import TYPE_CHECKING

from fastapi import status

from app.main import app

if TYPE_CHECKING:
    from httpx import AsyncClient


async def test_ping(client: "AsyncClient") -> None:
    response = await client.get(app.other_asgi_app.url_path_for("ping"))
    assert response.json() == {"status": "OK"}, response.json()
    assert response.status_code == status.HTTP_200_OK, response.json()
