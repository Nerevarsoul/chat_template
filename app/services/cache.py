from loguru import logger

from app import config
from app.clients import cache

SID_BY_USER_ID_KEY_PREFIX = "SID_BY_USER_ID:"
USER_ID_BY_SID_KEY_PREFIX = "USER_ID_BY_SID:"
ONLINE_USER_KEY = "ONLINE_USER_KEY"


async def create_sid_cache(user_uid: str, sid: str) -> None:
    pipe = cache.pipeline()

    pipe.sadd(f"{SID_BY_USER_ID_KEY_PREFIX}{user_uid}", sid)
    pipe.expire(f"{SID_BY_USER_ID_KEY_PREFIX}{user_uid}", config.cache.user_sid_cache_lifetime)

    pipe.set(f"{USER_ID_BY_SID_KEY_PREFIX}{sid}", user_uid, ex=config.cache.user_sid_cache_lifetime)

    pipe.sadd(ONLINE_USER_KEY, user_uid)
    await pipe.execute()


async def remove_sid_cache(sid: str) -> None:
    user_uid = await get_user_uid_by_sid(sid)
    logger.debug(f"User Id from cache: {user_uid}")
    pipe = cache.pipeline()
    pipe.delete(f"{USER_ID_BY_SID_KEY_PREFIX}{sid}")
    if user_uid:
        logger.debug(f"User key: {SID_BY_USER_ID_KEY_PREFIX}{user_uid}")
        pipe.srem(f"{SID_BY_USER_ID_KEY_PREFIX}{user_uid}", sid)
        pipe.srem(ONLINE_USER_KEY, user_uid)
    await pipe.execute()


async def get_user_uid_by_sid(sid: str) -> None | str:
    return await cache.get(f"{USER_ID_BY_SID_KEY_PREFIX}{sid}")


async def get_all_sid_by_user_uid(user_uid: str) -> set[str]:
    return await cache.smembers(f"{SID_BY_USER_ID_KEY_PREFIX}{user_uid}")


async def get_online_users() -> set[str]:
    return await cache.smembers(ONLINE_USER_KEY)


async def get_online_session(recipients_data: dict[str, list], sid: str) -> dict[str, list]:
    sender_uid = await get_user_uid_by_sid(sid)
    if sender_uid:
        del recipients_data[sender_uid]
    recipients_uid = recipients_data.keys()

    pipe = cache.pipeline()
    for user_uid in recipients_uid:
        pipe.smembers(f"{SID_BY_USER_ID_KEY_PREFIX}{user_uid}")
    res = await pipe.execute()

    for recipient_uid, recipient_sid in list(zip(recipients_uid, res)):
        if recipient_sid:
            recipients_data[recipient_uid].extend(list(recipient_sid))
    return recipients_data
