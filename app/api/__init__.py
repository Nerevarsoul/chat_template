from fastapi import APIRouter

from . import chats, contacts, monitoring

router = APIRouter(prefix="/chat")

router.include_router(monitoring.router, tags=["monitoring"])
router.include_router(chats.router, tags=["chats"])
router.include_router(contacts.router, tags=["contacts"])
