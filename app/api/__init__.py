from fastapi import APIRouter

from . import monitoring

router = APIRouter()

router.include_router(monitoring.router, tags=["monitoring"])
