import uuid

import factory
import pytest

from app.db.models import User
from app.db.registry import registry
from tests.app.db.utils import AsyncSQLAlchemyFactory


class UserFactory(AsyncSQLAlchemyFactory):
    uid = factory.LazyFunction(uuid.uuid4)
    name = factory.Faker("pystr", min_chars=10, max_chars=20)

    class Meta:
        model = User
        sqlalchemy_session = lambda: registry.session


@pytest.fixture
def user_db_f() -> type[UserFactory]:
    return UserFactory
