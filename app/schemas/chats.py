from pydantic import BaseModel

from app.db.enums import ChatState, ChatUserRole


class Chat(BaseModel):
    id: int
    state: ChatState
    chat_name: str
    user_chat_state: ChatState
    user_role: ChatUserRole
