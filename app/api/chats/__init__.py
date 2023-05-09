from fastapi import APIRouter

from . import routers

router = APIRouter()

router.include_router(routers.router, tags=["chats"])
