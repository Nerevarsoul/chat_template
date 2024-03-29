from itertools import chain

from fastapi import HTTPException, status
from loguru import logger
from pydantic.types import UUID4
from sqlalchemy import and_, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import coalesce
from starlette.datastructures import Headers

from app import config, db, sio
from app.db.enums import MessageType
from app.db.registry import registry
from app.schemas import sio as s_sio
from app.services import cache as cache_service
from app.services.utils import check_user_uid_by_sid
from app.sio.constants import NAMESPACE

DELETED_MESSAGE_TEXT = "deleted"


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


@check_user_uid_by_sid
async def process_create_message(sio_payload: dict, sid: str) -> None:
    saved_message_data = await _save_message(s_sio.NewMessagePayload(**sio_payload))

    if saved_message_data:
        sio_payload["id"] = saved_message_data[0]
        sio_payload["time_created"] = saved_message_data[1].timestamp()
        await _send_message(
            message=sio_payload,
            event_name=s_sio.SioEvents.MESSAGE_NEW,
            sid=sid,
            send_to_offline=True,
        )


@check_user_uid_by_sid
async def process_edit_message(sio_payload: dict, sid: str) -> None:
    edited_message_data = await _update_message(s_sio.EditMessagePayload(**sio_payload))

    if not edited_message_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    sio_payload["time_updated"] = edited_message_data[0].timestamp()
    await _send_message(
        message=sio_payload,
        event_name=s_sio.SioEvents.MESSAGE_CHANGE,
        sid=sid,
    )


@check_user_uid_by_sid
async def process_typing(sio_payload: dict, sid: str) -> None:
    s_sio.BasePayload(**sio_payload)  # Validate chat_id and user_uid in payload

    await _send_message(
        message=sio_payload,
        event_name=s_sio.SioEvents.TYPING,
        sid=sid,
    )


@check_user_uid_by_sid
async def process_delete_messages(sio_payload: dict, sid: str) -> None:
    deleted_messages_data = await _delete_messages(s_sio.DeleteMessagesPayload(**sio_payload))

    if not deleted_messages_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    del sio_payload["message_ids"]
    for row in deleted_messages_data:
        sio_payload["text"] = DELETED_MESSAGE_TEXT
        sio_payload["id"] = row.id
        sio_payload["time_updated"] = row.time_updated.timestamp()
        await _send_message(
            message=sio_payload,
            event_name=s_sio.SioEvents.MESSAGE_CHANGE,
            sid=sid,
        )


async def _save_message(message_for_saving: s_sio.NewMessagePayload) -> tuple | None:
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


async def _update_unread_counter(message: s_sio.NewMessagePayload, session: AsyncSession) -> None:
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


async def _update_message(message_for_update: s_sio.EditMessagePayload) -> tuple | None:
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


async def _delete_messages(message_for_delete: s_sio.DeleteMessagesPayload) -> list:
    async with registry.session() as session:
        delete_messages_query = (
            update(db.Message)
            .values(
                text=DELETED_MESSAGE_TEXT,
                search_text=func.to_tsvector(coalesce(DELETED_MESSAGE_TEXT, "")),
                type_=MessageType.DELETED,
            )
            .where(
                and_(
                    db.Message.id.in_(message_for_delete.message_ids),
                    db.Message.user_uid == message_for_delete.user_uid,
                    db.Message.type_ != MessageType.DELETED,
                )
            )
        )
        deleted_messages_data = (
            await session.execute(delete_messages_query.returning(db.Message.id, db.Message.time_updated))
        ).all()

        await session.commit()
    return deleted_messages_data


async def _send_message(
    message: dict,
    event_name: str,
    sid: str = "",
    send_to_offline: bool = False,
) -> None:
    recipients_uid = await _get_recipients_uid(message["chat_id"])
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
            await _send_ofline_message(
                recipients_uid=offline_recipients_uid, message=message, sender_uid=message["sender_id"]
            )


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
