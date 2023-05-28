from loguru import logger
from sqlalchemy import select
from starlette.datastructures import Headers

from app import config, db
from app.db.registry import registry
from app.schemas.sio import SioEvents


async def connect(sid: str, environ: dict) -> str | None:
    print(environ["asgi.scope"]["headers"])
    headers = Headers(raw=environ["asgi.scope"]["headers"])
    print(headers)
    logger.debug(f"headers - {headers}")
    user_id = headers.get(config.application.user_header_name)
    if not user_id:
        return SioEvents.USER_MISSING
    query = select(db.User).where(db.User.uid == user_id)
    async with registry.session() as session:
        if not (await session.execute(query)).scalar():
            return SioEvents.USER_NOT_FOUND
    logger.debug(f"User id - {user_id}")
    logger.info(f"Connect user: {user_id} with sid: {sid}")
