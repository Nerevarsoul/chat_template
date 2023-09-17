from loguru import logger
from sqlalchemy import func, select, update, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql.functions import coalesce
from starlette.datastructures import Headers

from app import config, db
from app.db.enums import MessageType
from app.db.registry import registry
from app.schemas import sio as s_sio
from app.services import cache as cache_service


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
    await cache_service.create_sid_cache(user_id, sid)
    logger.info(f"Connect user: {user_id} with sid: {sid}")


async def disconnect(sid: str) -> None:
    await cache_service.remove_sid_cache(sid)


async def save_message(message_for_saving: s_sio.NewMessage) -> bool:
    async with registry.session() as session:
        insert_message_query = (
            pg_insert(db.Message)
            .values(
                **message_for_saving.model_dump(),
                search_text=func.to_tsvector(coalesce(message_for_saving.text.lower(), "")),
                type_=MessageType.FROM_USER,
            )
            .on_conflict_do_nothing(
                constraint="messages_client_id_key",
            )
        )
        res = await session.execute(insert_message_query)

        is_inserted = res.is_insert and res.rowcount == 1

        if is_inserted:
            update_unread_counter_query = (
                update(db.ChatRelationship)
                .values(unread_counter=db.ChatRelationship.unread_counter + 1)
                .where(
                    and_(
                        db.ChatRelationship.chat_id == message_for_saving.chat_id,
                        db.ChatRelationship.user_uid != message_for_saving.user_uid,
                    )
                )
            )
            await session.execute(update_unread_counter_query)

        await session.commit()
    return is_inserted


async def process_message(new_message: dict) -> bool:
    return await save_message(s_sio.NewMessage(**new_message))
