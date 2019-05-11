import pytest

pytestmark = pytest.mark.asyncio


async def test_me(async_spotify_user_auth):
    assert await async_spotify_user_auth.me()


async def test_user_profile(async_spotify_user_auth, john_smith_user_id):
    assert await async_spotify_user_auth.user_profile(john_smith_user_id)
