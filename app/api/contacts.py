from fastapi import APIRouter, Depends, status
from pydantic.types import UUID4

from app.schemas import common as s_common
from app.schemas import contacts as s_contacts
from app.services import contacts as contacts_service
from app.services.utils import get_current_user

router = APIRouter(prefix="/contacts")


@router.post("/put_notifications_token", response_model=s_common.ChatApiResponse, status_code=status.HTTP_200_OK)
async def put_notifications_token(
    data: s_contacts.TokenData, current_user_uid: UUID4 = Depends(get_current_user)
) -> s_common.ChatApiResponse:
    return await contacts_service.save_device_token(current_user_uid, data)
