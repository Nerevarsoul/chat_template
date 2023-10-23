from itertools import chain

from fastapi import HTTPException, status
from loguru import logger
from pydantic.types import UUID4
from sqlalchemy import and_, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql.functions import coalesce
from starlette.datastructures import Headers

from app import config, db, sio
from app.db.enums import MessageType
from app.db.registry import _DBRegistry, registry
from app.schemas import sio as s_sio
from app.services import cache as cache_service
from app.services.utils import check_user_uid_by_sid
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


async def process_create_message(new_message: dict, sid: str) -> None:
    saved_message_data = await _save_message(s_sio.NewMessage(**new_message))
    if saved_message_data:
        new_message["id"] = saved_message_data[0]
        new_message["time_created"] = saved_message_data[1].timestamp()
        await _send_message(
            message=new_message,
            chat_id=new_message["chat_id"],
            sender_uid=new_message["user_uid"],
            event_name=s_sio.SioEvents.MESSAGE_NEW,
            sid=sid,
            send_to_offline=True,
        )


@check_user_uid_by_sid
async def process_edit_message(message: dict, sid: str) -> None:
    edited_message_data = await _update_message(s_sio.EditMessageData(**message))

    if not edited_message_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    message["time_updated"] = edited_message_data[0].timestamp()
    await _send_message(
        message=message,
        chat_id=message["chat_id"],
        sender_uid=message["user_uid"],
        event_name=s_sio.SioEvents.MESSAGE_CHANGE,
        sid=sid,
    )


async def _save_message(message_for_saving: s_sio.NewMessage) -> tuple | None:
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
        saved_message_data = (
            await session.execute(insert_message_query.returning(db.Message.id, db.Message.time_created))
        ).first()

        if saved_message_data:
            await _update_unread_counter(message_for_saving, session)

        await session.commit()
    return saved_message_data


async def _update_unread_counter(message: s_sio.NewMessage, session: _DBRegistry) -> None:
    update_unread_counter_query = (
        update(db.ChatRelationship)
        .values(unread_counter=db.ChatRelationship.unread_counter + 1)
        .where(
            and_(
                db.ChatRelationship.chat_id == message.chat_id,
                db.ChatRelationship.user_uid != message.user_uid,
            )
        )
    )

    await session.execute(update_unread_counter_query)


async def _update_message(message_for_update: s_sio.EditMessageData) -> tuple | None:
    async with registry.session() as session:
        update_message_query = (
            update(db.Message)
            .values(
                text=message_for_update.text,
                search_text=func.to_tsvector(coalesce(message_for_update.text.lower(), "")),
            )
            .where(
                and_(
                    db.Message.id == message_for_update.message_id,
                    db.Message.user_uid == message_for_update.user_uid,
                )
            )
        )
        updated_message_data = (await session.execute(update_message_query.returning(db.Message.time_updated))).first()

        await session.commit()
    return updated_message_data


async def _send_message(
    message: dict,
    chat_id: int,
    sender_uid: UUID4,
    event_name: str,
    sid: str = "",
    send_to_offline: bool = False,
) -> None:
    recipients_uid = await _get_recipients_uid(chat_id)
    logger.debug(f"Recipients for - {event_name} - {recipients_uid}")
    recipients_data = await cache_service.get_online_session(recipients_uid=recipients_uid)
    online_recipients_sid = _get_online_recipients_sid(recipients_data)
    if online_recipients_sid:
        logger.debug(f"Online recipients for - {event_name} - {online_recipients_sid}")
        await _send_online_message(recipients_sid=online_recipients_sid, message=message, event_name=event_name)
    if send_to_offline:
        offline_recipients_uid = _get_offline_recipients_uid(recipients_data)
        if offline_recipients_uid:
            logger.debug(f"Online recipients for - {event_name} - {offline_recipients_uid}")
            await _send_ofline_message(recipients_uid=offline_recipients_uid, message=message, sender_uid=sender_uid)


async def _get_recipients_uid(chat_id: int) -> list[str]:
    query = select(db.ChatRelationship.user_uid).where(db.ChatRelationship.chat_id == chat_id)
    async with registry.session() as session:
        chat_recipients = await session.execute(query)

    return [str(recipient_uid) for recipient_uid in chat_recipients.scalars()]


def _get_online_recipients_sid(recipients_data: dict[str, set]) -> list[str]:
    return [recipient_sid for recipient_sid in chain(*recipients_data.values()) if recipient_sid != set()]


def _get_offline_recipients_uid(recipients_data: dict[str, set]) -> list[str]:
    return [recipient_data[0] for recipient_data in recipients_data.items() if recipient_data[1] == set()]


async def _send_online_message(recipients_sid: list[str], message: dict, event_name: str) -> None:
    logger.info(f"Send {event_name} message - {message} to {recipients_sid}")
    for sid in recipients_sid:
        await sio.sio.emit(event=event_name, data=message, to=sid, namespace=NAMESPACE)


async def _send_ofline_message(recipients_uid: list[str], message: dict, sender_uid: UUID4) -> None:
    pass
