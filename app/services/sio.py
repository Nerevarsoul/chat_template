from typing import TYPE_CHECKING

from loguru import logger
from socketio import AsyncServer
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql.functions import coalesce
from starlette.datastructures import Headers

from app import config, db
from app.db.enums import MessageType
from app.db.registry import registry
from app.schemas import chats as s_chat
from app.schemas import sio as s_sio
from app.services import cache as cache_service
from app.sio.constants import NAMESPACE


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


async def process_message(sio: AsyncServer, new_message: dict, sid: str) -> None:
    saved_message = await _save_message(s_sio.NewMessage(**new_message))
    if saved_message:
        message = s_chat.Message.model_validate(saved_message).model_dump()
        await _send_message(
            sio=sio,
            message=message,
            chat_id=message["chat_id"],
            sender_uid=str(message["user_uid"]),
            event_name="srv:msg:new",
            sid=sid,
            send_to_offline=True,
        )


async def _save_message(message_for_saving: s_sio.NewMessage) -> db.Message | None:
    async with registry.session() as session:
        query = (
            insert(db.Message)
            .values(
                **message_for_saving.model_dump(),
                search_text=func.to_tsvector(coalesce(message_for_saving.text.lower(), "")),
                type_=MessageType.FROM_USER,
            )
            .on_conflict_do_nothing(
                constraint="messages_client_id_key",
            )
        )
        saved_message = await session.execute(query.returning(db.Message))
        await session.commit()
    return saved_message.scalar()


async def _send_message(
    sio: AsyncServer,
    message: dict,
    chat_id: int,
    sender_uid: str,
    event_name: str,
    sid: str = "",
    send_to_offline: bool = False,
) -> None:
    recipients_uid = await _get_recipients_uid(chat_id)
    logger.debug(f"Recipients for - {event_name} - {recipients_uid}")
    online_recipients_sid, offline_recipients_uid = await cache_service.get_online_session(
        recipients_uid=recipients_uid, sid=sid
    )
    logger.debug(f"Online recipients for - {event_name} - {online_recipients_sid}")
    if online_recipients_sid:
        await _send_online_message(
            sio=sio, recipients_sid=online_recipients_sid, message=message, event_name=event_name
        )
    if send_to_offline and offline_recipients_uid:
        await _send_ofline_message(recipients_uid=offline_recipients_uid, message=message, sender_uid=sender_uid)


async def _get_recipients_uid(chat_id: int) -> list[str]:
    query = select(db.ChatRelationship.user_uid).where(db.ChatRelationship.chat_id == chat_id)
    async with registry.session() as session:
        chat_recipients = await session.execute(query)
    return [str(recipient_uid) for recipient_uid in chat_recipients.scalars()]


async def _send_online_message(sio: AsyncServer, recipients_sid: list[str], message: dict, event_name: str) -> None:
    logger.info(f"Send {event_name} message - {message} to {recipients_sid}")
    for sid in recipients_sid:
        await sio.emit(event=event_name, data=message, to=sid, namespace=NAMESPACE)


async def _send_ofline_message(recipients_uid: list[str], message: dict, sender_uid: str) -> None:
    pass
