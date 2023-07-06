import uuid

import pytest

from app.services import cache as cache_service


@pytest.mark.usefixtures("clear_cache")
async def test_create_sid_cache():
    user_uid = str(uuid.uuid4())
    sid = str(uuid.uuid4())
    await cache_service.create_sid_cache(user_uid, sid)

    assert user_uid == await cache_service.get_user_uid_by_sid(sid)
    assert {sid} == await cache_service.get_all_sid_by_user_uid(user_uid)
    assert {user_uid} == await cache_service.get_online_users()


@pytest.mark.usefixtures("clear_cache")
async def test_remove_sid_cache():
    user_uid = str(uuid.uuid4())
    sid = str(uuid.uuid4())
    await cache_service.create_sid_cache(user_uid, sid)
    await cache_service.remove_sid_cache(sid)

    assert await cache_service.get_user_uid_by_sid(sid) is None
    assert set() == await cache_service.get_all_sid_by_user_uid(user_uid)
    assert set() == await cache_service.get_online_users()
