from sqlalchemy import select

from app.db.models import User
from app.db.registry import registry


async def test_user_factory(user_db_f):
    user = await user_db_f.create()

    async with registry.session() as session:
        user_from_db = (await session.execute(select(User).where(User.uid == user.uid))).scalars().first()

        assert user_from_db
        assert user_from_db.name == user.name
