from fastapi import Header, HTTPException, status
from sqlalchemy import select

from app.db import User
from app.db.registry import registry


async def get_current_user(user_id: str | None = Header(default=None)):
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    async with registry.session() as session:
        user = (await session.execute(select(User).where(User.uid == user_id))).scalars().first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user_id
