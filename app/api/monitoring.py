from fastapi import APIRouter

router = APIRouter()


@router.get("/ping", responses={"200": {"content": {"application/json": {"example": {"status": "OK"}}}}})
async def ping():
    """Health check for service"""
    return {"status": "OK"}
