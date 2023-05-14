from pydantic_factories import ModelFactory

from app.api.chats.schemas import CreateChatData


class CreateChatDataFactory(ModelFactory):
    __model__ = CreateChatData
