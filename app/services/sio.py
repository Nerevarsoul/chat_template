from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.sql.functions import coalesce
from starlette.datastructures import Headers

from app import config, db
from app.db.enums import MessageType
from app.db.registry import registry
from app.schemas import sio as s_sio
from app.schemas.sio import SioEvents


async def connect(sid: str, environ: dict) -> str | None:
    headers = Headers(raw=environ["asgi.scope"]["headers"])
    logger.debug(f"headers - {headers}")
    user_id = headers.get(config.application.user_header_name)
    if not user_id:
        return SioEvents.USER_MISSING
    query = select(db.User).where(db.User.uid == user_id)
    async with registry.session() as session:
        if not (await session.execute(query)).scalar():
            return SioEvents.USER_MISSING
    logger.debug(f"User id - {user_id}")
    logger.info(f"Connect user: {user_id} with sid: {sid}")


async def save_message(new_message: s_sio.NewMessage) -> db.Message:
    async with registry.session() as session:
        new_message = db.Message(
            user_uid=new_message.sender_id,
            chat_id=new_message.chat_id,
            text=new_message.text,
            search_text=func.to_tsvector(coalesce(new_message.text.lower(), "")),
            type_=MessageType.FROM_USER,
        )
        session.add(new_message)
        await session.commit()
    return new_message


async def process_message(new_message: s_sio.NewMessage):
    saved_message = await save_message(new_message)
