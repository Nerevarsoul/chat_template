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


@pytest.mark.usefixtures("clear_cache")
async def test_get_online_session():
    users_uid = [str(uuid.uuid4()) for _ in range(4)]
    users_sid = [str(uuid.uuid4()) for _ in range(3)]
    await cache_service.create_sid_cache(users_uid[0], users_sid[0])
    await cache_service.create_sid_cache(users_uid[1], users_sid[1])
    await cache_service.create_sid_cache(users_uid[1], users_sid[2])

    recipients_data = await cache_service.get_online_session(recipients_uid=users_uid)

    assert len(recipients_data.keys()) == 4

    assert users_uid[0] in recipients_data.keys()
    assert recipients_data[users_uid[0]] == {users_sid[0]}
    assert users_uid[1] in recipients_data.keys()
    assert recipients_data[users_uid[1]] == {users_sid[1], users_sid[2]}
    assert users_uid[2] in recipients_data.keys()
    assert recipients_data[users_uid[2]] == set()
    assert users_uid[3] in recipients_data.keys()
    assert recipients_data[users_uid[3]] == set()
