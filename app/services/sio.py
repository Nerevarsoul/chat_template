from loguru import logger
from starlette.datastructures import Headers

from app import config
from app.schemas.sio import SioEvents


async def connect(sid: str, environ: dict) -> str | None:
    print(environ["asgi.scope"]["headers"])
    headers = Headers(raw=environ["asgi.scope"]["headers"])
    print(headers)
    logger.debug(f"headers - {headers}")
    user_id = headers.get(config.application.user_header_name)
    if not user_id:
        return SioEvents.USER_MISSING
    logger.debug(f"User id - {user_id}")
    logger.info(f"Connect user: {user_id} with sid: {sid}")
