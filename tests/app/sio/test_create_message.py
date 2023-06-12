import pytest
from sqlalchemy import func, select

from app.db.enums import MessageType
from app.db.models import Message
from app.db.registry import registry
from app.services import sio as sio_service
from tests.factories.schemas import NewMessageFactory


@pytest.mark.usefixtures("clear_db")
async def test_create_message(user_db_f, chat_db_f):
    user = await user_db_f.create()
    chat = await chat_db_f.create()
    new_message = NewMessageFactory.build(sender_id=user.uid, chat_id=chat.id)

    event = await sio_service.process_message(new_message=new_message.dict())
    assert event is None

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == chat.id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 1

    async with registry.session() as session:
        query = select(Message).where(Message.chat_id == chat.id)
        message = (await session.execute(query)).scalar()
    assert message.user_uid == user.uid
    assert message.chat_id == chat.id
    assert message.text == new_message.text
    assert message.type_ == MessageType.FROM_USER


@pytest.mark.usefixtures("clear_db")
async def test_create_empty_message(user_db_f, chat_db_f):
    user = await user_db_f.create()
    chat = await chat_db_f.create()
    new_message = NewMessageFactory.build(factory_use_construct=True, sender_id=user.uid, chat_id=chat.id, text="")

    with pytest.raises(Exception) as exc:
        await sio_service.process_message(new_message=new_message.dict())
    assert exc.typename == "ValidationError"

    async with registry.session() as session:
        query = select(func.count()).select_from(Message).where(Message.chat_id == chat.id)
        messages_quantity = (await session.execute(query)).scalar()
    assert messages_quantity == 0
