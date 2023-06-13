from pydantic_factories import ModelFactory

from app.schemas import sio as s_sio
from app.schemas.chats import CreateChatData


class CreateChatDataFactory(ModelFactory):
    __model__ = CreateChatData


class NewMessageFactory(ModelFactory):
    __model__ = s_sio.NewMessage
