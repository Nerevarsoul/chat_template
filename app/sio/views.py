import socketio
from loguru import logger
from starlette.datastructures import Headers

from app import config
from app.sio.constants import NAMESPACE, USER_HEADER_NAME

sio = socketio.AsyncServer(
    async_mode="asgi",
    allow_upgrades=True,
    # client_manager=socketio.AsyncRedisManager(url=config.cache.dsn),
    ping_timeout=config.socketio.ping_timeout,
    ping_interval=config.socketio.ping_interval,
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
)


@sio.on("connect", namespace=NAMESPACE)
async def connect_handler(sid: str, environ: dict):
    headers = Headers(raw=environ["asgi.scope"]["headers"])
    logger.debug(f"headers - {headers}")
    user_id = headers.get(USER_HEADER_NAME)
    logger.debug(f"User id - {user_id}")
    logger.info(f"Connect user: {user_id} with sid: {sid}")


@sio.on("disconnect", namespace=NAMESPACE)
async def disconnect_handler(sid: str):
    logger.info(f"Disconnect user: {sid}")
