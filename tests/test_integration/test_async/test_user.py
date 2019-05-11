from pyfy import Spotify
import pytest

pytestmark = pytest.mark.asyncio


async def test_follow_user(async_spotify_user_auth, john_smith_user_id):
    assert await async_spotify_user_auth.follow_users(john_smith_user_id) is not None


async def test_follow_users(
    async_spotify_user_auth, john_smith_user_id, spotify_test_user_id
):
    assert (
        await async_spotify_user_auth.follow_users(
            [john_smith_user_id, spotify_test_user_id]
        )
        is not None
    )


async def test_follows_user(async_spotify_user_auth, john_smith_user_id):
    assert await async_spotify_user_auth.follows_users(john_smith_user_id) is not None


async def test_follows_users(
    async_spotify_user_auth, john_smith_user_id, spotify_test_user_id
):
    assert (
        await async_spotify_user_auth.follows_users(
            [john_smith_user_id, spotify_test_user_id]
        )
        is not None
    )


async def test_unfollow_user(async_spotify_user_auth, john_smith_user_id):
    assert await async_spotify_user_auth.unfollow_users(john_smith_user_id) is not None


async def test_unfollow_users(
    async_spotify_user_auth, john_smith_user_id, spotify_test_user_id
):
    assert (
        await async_spotify_user_auth.unfollow_users(
            [john_smith_user_id, spotify_test_user_id]
        )
        is not None
    )


async def test_user_top_tracks(async_spotify_user_auth):
    assert await async_spotify_user_auth.user_top_tracks()
