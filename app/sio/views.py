import socketio
from loguru import logger

from app import config
from app.services import sio as sio_service
from app.sio.constants import NAMESPACE

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
async def connect_handler(sid: str, environ: dict) -> None:
    event = await sio_service.connect(sid, environ)
    if event:
        await sio.emit(event, {}, room=sid, namespace=NAMESPACE)


@sio.on("disconnect", namespace=NAMESPACE)
async def disconnect_handler(sid: str) -> None:
    await sio_service.disconnect(sid)
    logger.info(f"Disconnect user: {sid}")


@sio.on("usr:msg:create", namespace=NAMESPACE)
async def create_message_handler(sid: str, new_message: dict) -> dict:
    logger.debug(f"Receive message: {new_message}")
    try:
        await sio_service.process_message(new_message, sid)
        return {"result": {"success": True}}
    except Exception as e:
        return {"error": str(e), "error_code": 500}


@sio.on("usr:msg:edit", namespace=NAMESPACE)
async def edit_message_handler(sid: str, message: dict) -> dict:
    logger.debug(f"Edit message: {message}")
    try:
        await sio_service.process_edit_message(message, sid)
        return {"result": {"success": True}}
    except Exception as e:
        return {"error": str(e), "error_code": 500}
