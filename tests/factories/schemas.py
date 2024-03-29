from polyfactory.factories.pydantic_factory import ModelFactory

from app.schemas import chats as s_chats
from app.schemas import common as s_common
from app.schemas import contacts as s_contacts
from app.schemas import sio as s_sio


class CreateChatDataFactory(ModelFactory):
    __model__ = s_chats.CreateChatData


class SioNewMessagePayloadFactory(ModelFactory):
    __model__ = s_sio.NewMessagePayload


class SioEditMessagePayloadFactory(ModelFactory):
    __model__ = s_sio.EditMessagePayload


class SioBasePayloadFactory(ModelFactory):
    __model__ = s_sio.BasePayload


class SioDeleteMessagesPayloadFactory(ModelFactory):
    __model__ = s_sio.DeleteMessagesPayload


class TokenDataFactory(ModelFactory):
    __model__ = s_contacts.TokenData


class SuccessfulResultFactory(ModelFactory):
    __model__ = s_common.Result
    __set_as_default_factory_for_type__ = True

    success = True


class SuccessfulChatApiResponseFactory(ModelFactory):
    __model__ = s_common.ChatApiResponse
