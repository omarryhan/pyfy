import pytest

pytestmark = pytest.mark.asyncio


async def test_followed_artists(async_spotify_user_auth):
    assert await async_spotify_user_auth.followed_artists() is not None


async def test_follow_artist(async_spotify_user_auth, test_artist_id):
    assert await async_spotify_user_auth.follow_artists(test_artist_id) is not None


async def test_follow_artists(
    async_spotify_user_auth, test_artist_id, testing_funny_artist_id
):
    assert (
        await async_spotify_user_auth.follow_artists(
            [test_artist_id, testing_funny_artist_id]
        )
        is not None
    )


async def test_follows_artist(async_spotify_user_auth, test_artist_id):
    assert await async_spotify_user_auth.follows_artists(test_artist_id) is not None


async def test_follows_artists(
    async_spotify_user_auth, test_artist_id, testing_funny_artist_id
):
    assert (
        await async_spotify_user_auth.follow_artists(
            [test_artist_id, testing_funny_artist_id]
        )
        is not None
    )


async def test_unfollow_artist(async_spotify_user_auth, test_artist_id):
    assert await async_spotify_user_auth.unfollow_artists(test_artist_id) is not None


async def test_unfollow_artists(
    async_spotify_user_auth, test_artist_id, testing_funny_artist_id
):
    assert (
        await async_spotify_user_auth.unfollow_artists(
            [test_artist_id, testing_funny_artist_id]
        )
        is not None
    )


async def test_artist(async_spotify_user_auth, depeche_mode_artist_id):
    assert await async_spotify_user_auth.artists(depeche_mode_artist_id)


async def test_artists(
    async_spotify_user_auth, rammstein_artist_id, depeche_mode_artist_id
):
    assert await async_spotify_user_auth.artists(
        [rammstein_artist_id, depeche_mode_artist_id]
    )


async def test_artist_related_artists(async_spotify_user_auth, depeche_mode_artist_id):
    assert await async_spotify_user_auth.artist_related_artists(depeche_mode_artist_id)
