import pytest
from sqlalchemy import func, select

from app.db.models import Message
from app.db.registry import registry
from app.services import sio as sio_service
from tests.factories.schemas import NewMessageFactory


@pytest.mark.usefixtures("clear_db")
async def test_create_message(user_db_f, chat_db_f):
    user = await user_db_f.create()
    chat = await chat_db_f.create()
    new_message = NewMessageFactory.build(sender_id=user.uid, chat_id=chat.id, client_id=user.uid)

    event = await sio_service.process_message(new_message=new_message)
    assert event is None

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == chat.id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 1
