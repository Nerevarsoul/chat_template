import uuid

import factory
import pytest

from app import db
from app.db.enums import ChatState, ChatUserRole, MessageType
from app.db.registry import registry
from tests.app.db.utils import AsyncSQLAlchemyFactory


class UserFactory(AsyncSQLAlchemyFactory):
    uid = factory.LazyFunction(uuid.uuid4)
    name = factory.Faker("pystr", min_chars=10, max_chars=20)

    class Meta:
        model = db.User
        async_alchemy_get_or_create = ("uid",)
        sqlalchemy_session = lambda: registry.session


class ChatFactory(AsyncSQLAlchemyFactory):
    id = factory.Faker("pyint")
    state = ChatState.ACTIVE
    time_created = factory.Faker("past_datetime")
    time_updated = factory.Faker("past_datetime")

    class Meta:
        model = db.Chat
        async_alchemy_get_or_create = ("id",)
        sqlalchemy_session = lambda: registry.session


class ChatRelationshipFactory(AsyncSQLAlchemyFactory):
    user_uid = factory.SelfAttribute("user.uid")
    chat_id = factory.SelfAttribute("chat.id")
    chat_name = factory.Faker("pystr", min_chars=10, max_chars=30)
    state = ChatState.ACTIVE
    last_read_message_id = None
    unread_counter = 0
    time_pinned = None
    user_role = ChatUserRole.USER

    chat = factory.SubFactory(ChatFactory)
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = db.ChatRelationship
        sqlalchemy_session = lambda: registry.session


class MessageFactory(AsyncSQLAlchemyFactory):
    id = factory.Sequence(int)
    user_uid = factory.LazyFunction(uuid.uuid4)
    chat_id = factory.Faker("pyint")
    client_id = factory.LazyFunction(uuid.uuid4)
    text = factory.Faker("pystr", min_chars=10, max_chars=30)
    search_text = factory.Faker("pystr", min_chars=10, max_chars=30)
    type_ = MessageType.FROM_USER
    quoted_message = None
    mentions = None
    links = None
    original_id = None
    original_chat_id = None
    time_created = factory.Faker("past_datetime")
    time_updated = None

    class Meta:
        model = db.Message
        sqlalchemy_session = lambda: registry.session


@pytest.fixture
def user_db_f() -> type[UserFactory]:
    return UserFactory


@pytest.fixture
def chat_db_f() -> type[ChatFactory]:
    return ChatFactory


@pytest.fixture
def chat_relationship_db_f() -> type[ChatRelationshipFactory]:
    return ChatRelationshipFactory


@pytest.fixture
def message_db_f() -> type[MessageFactory]:
    return MessageFactory
