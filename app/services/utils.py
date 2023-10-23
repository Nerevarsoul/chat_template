import uuid
from functools import wraps
from typing import Awaitable, Callable, TypeVar

from fastapi import Header, HTTPException, status
from pydantic.types import UUID4
from sqlalchemy import select

from app.db import User
from app.db.registry import registry
from app.services import cache as cache_service

T = TypeVar("T")


async def get_current_user(user_id: str | None = Header(default=None)) -> UUID4:
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    async with registry.session() as session:
        user = (await session.execute(select(User).where(User.uid == user_id))).scalars().first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return uuid.UUID(user_id)


def check_user_uid_by_sid(coro: Callable[[dict, str], Awaitable[T]]) -> Callable[[dict, str], Awaitable[T]]:
    @wraps(coro)
    async def wrapped(message: dict, sid: str) -> T:
        user_uid = await cache_service.get_user_uid_by_sid(sid)
        if message["sender_id"] != user_uid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
        return await coro(message, sid)

    return wrapped
