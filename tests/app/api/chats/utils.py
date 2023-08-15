from pydantic.types import UUID4

from app import db
from app.db.enums import ChatUserRole


async def generate_chat_history(user: db.User, chat_relationship_db_f, count: int = 1):
    for i in range(count):
        rel = await chat_relationship_db_f.create(user=user, user_role=ChatUserRole.CREATOR)
        await chat_relationship_db_f.create(chat=rel.chat)


async def get_sorted_messages_id_list(
    messages_count: int, user_uid: UUID4, chat_id: int, message_db_f, reverse: bool = False
) -> list[int]:
    messages = message_db_f.create_batch(messages_count, user_uid=user_uid, chat_id=chat_id)
    messages_id = [(await message).id for message in messages]
    return sorted(messages_id, reverse=not reverse)
