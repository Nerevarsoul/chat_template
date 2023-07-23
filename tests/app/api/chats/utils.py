from app import db
from app.db.enums import ChatUserRole


async def generate_chat_history(user: db.User, chat_relationship_db_f, count: int = 1):
    for i in range(count):
        rel = await chat_relationship_db_f.create(user=user, user_role=ChatUserRole.CREATOR)
        await chat_relationship_db_f.create(chat=rel.chat)
