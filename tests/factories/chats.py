from pydantic_factories import ModelFactory

from app.schemas.chats import CreateChatData


class CreateChatDataFactory(ModelFactory):
    __model__ = CreateChatData
