from fastapi import APIRouter

from . import chats, monitoring

router = APIRouter()

router.include_router(monitoring.router, tags=["monitoring"])
router.include_router(chats.router, tags=["chats"])
