from app.db.enums import ChatUserRole


async def generate_chat_history(user_uid: str, chat_relationship_db_f, count: int = 1):
    for i in range(count):
        rel = await chat_relationship_db_f.create(user__uid=user_uid, user_role=ChatUserRole.CREATOR)
        await chat_relationship_db_f.create(chat__id=rel.chat_id)
