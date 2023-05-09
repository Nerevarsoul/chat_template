from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

from app.db.models import User
from app.db.registry import registry


async def users_exist(users_uuid_list: list[UUID]) -> bool:
    async with registry.session() as session:
        for user_uuid in users_uuid_list:
            try:
                (await session.execute(select(User).where(User.uid == user_uuid))).one()
            except NoResultFound:
                return False
    return True
