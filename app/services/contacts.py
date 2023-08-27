from pydantic.types import UUID4
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app import db
from app.db.registry import registry
from app.schemas import common as s_common
from app.schemas import contacts as s_contacts


async def save_device_token(user_uid: UUID4, token_data: s_contacts.TokenData) -> s_common.ChatApiResponse:
    async with registry.session() as session:
        query = (
            pg_insert(db.Device)
            .values(
                user_uid=user_uid,
                token=token_data.token,
                platform=token_data.device_type,
            )
            .on_conflict_do_nothing(constraint="uqp_user_uid_platform")
        )

        await session.execute(query)
        await session.commit()

        return s_common.ChatApiResponse(result=s_common.Result(success=True))
