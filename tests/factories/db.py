import uuid

import factory
import pytest

from app import db
from app.db.enums import ChatState, ChatUserRole
from app.db.registry import registry
from tests.app.db.utils import AsyncSQLAlchemyFactory


class UserFactory(AsyncSQLAlchemyFactory):
    uid = factory.LazyFunction(uuid.uuid4)
    name = factory.Faker("pystr", min_chars=10, max_chars=20)

    class Meta:
        model = db.User
        sqlalchemy_session = lambda: registry.session


class ChatFactory(AsyncSQLAlchemyFactory):
    id = factory.Faker("pyint")
    state = ChatState.ACTIVE
    time_created = factory.Faker("past_datetime")
    time_updated = factory.Faker("past_datetime")

    class Meta:
        model = db.Chat
        sqlalchemy_session = lambda: registry.session


class ChatRelationshipFactory(AsyncSQLAlchemyFactory):
    user_uid = factory.LazyFunction(uuid.uuid4)
    chat_id = factory.Faker("pyint")
    chat_name = factory.Faker("pystr", min_chars=10, max_chars=30)
    state = ChatState.ACTIVE
    last_read_message_id = None
    unread_counter = 0
    is_pinned = False
    user_role = ChatUserRole.USER

    class Meta:
        model = db.ChatRelationship
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
