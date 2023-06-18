from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.sql.functions import coalesce
from starlette.datastructures import Headers

from app import config, db
from app.db.enums import MessageType
from app.db.registry import registry
from app.schemas import sio as s_sio


async def connect(sid: str, environ: dict) -> str | None:  # type: ignore[return]
    headers = Headers(raw=environ["asgi.scope"]["headers"])
    logger.debug(f"headers - {headers}")
    user_id = headers.get(config.application.user_header_name)
    if not user_id:
        return s_sio.SioEvents.USER_MISSING
    query = select(db.User).where(db.User.uid == user_id)
    async with registry.session() as session:
        if not (await session.execute(query)).scalar():
            return s_sio.SioEvents.USER_MISSING
    logger.debug(f"User id - {user_id}")
    logger.info(f"Connect user: {user_id} with sid: {sid}")


async def save_message(message_for_saving: s_sio.NewMessage) -> db.Message:
    async with registry.session() as session:
        new_message = db.Message(
            user_uid=message_for_saving.sender_id,
            chat_id=message_for_saving.chat_id,
            text=message_for_saving.text,
            search_text=func.to_tsvector(coalesce(message_for_saving.text.lower(), "")),
            type_=MessageType.FROM_USER,
        )
        session.add(new_message)
        await session.commit()
    return new_message


def validate_new_message(new_message: dict) -> s_sio.NewMessage:
    message_for_saving = s_sio.NewMessage(
        sender_id=new_message["sender_id"],
        chat_id=new_message["chat_id"],
        client_id=new_message["client_id"],
        text=new_message["text"],
    )
    return message_for_saving


async def process_message(new_message: dict) -> None:
    message_for_saving = validate_new_message(new_message)
    saved_message = await save_message(message_for_saving)
