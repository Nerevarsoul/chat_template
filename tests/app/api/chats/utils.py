from app.db.enums import ChatUserRole


async def generate_chat_history(user_uid: str, user_db_f, chat_db_f, chat_relationship_db_f, count: int = 1):
    for i in range(count):
        user = await user_db_f.create()
        chat = await chat_db_f.create()
        await chat_relationship_db_f.create(chat_id=chat.id, user_uid=user_uid, user_role=ChatUserRole.CREATOR)
        await chat_relationship_db_f.create(chat_id=chat.id, user_uid=user.uid)
