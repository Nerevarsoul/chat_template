from sqlalchemy import select

from app import db
from app.db.registry import registry


async def get_chat_list(user_id):
    query = (
        select(
            db.Chat.id,
            db.Chat.state,
            db.ChatRelationship.chat_name,
            db.ChatRelationship.state.label("user_chat_state"),
            db.ChatRelationship.user_role,
        )
        .outerjoin(db.ChatRelationship)
        .where(db.ChatRelationship.user_uid == user_id)
    )

    async with registry.session() as session:
        chat_list = (await session.execute(query)).scalars().all()

        return chat_list
