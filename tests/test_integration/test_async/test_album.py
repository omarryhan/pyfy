import pytest

pytestmark = pytest.mark.asyncio


async def test_save_album(async_spotify_user_auth, nothing_was_the_same_album_id):
    assert (
        await async_spotify_user_auth.save_albums(nothing_was_the_same_album_id)
        is not None
    )


async def test_save_albums(
    async_spotify_user_auth, scorpion_album_id, nothing_was_the_same_album_id
):
    assert (
        await async_spotify_user_auth.save_albums(
            [scorpion_album_id, nothing_was_the_same_album_id]
        )
        is not None
    )


async def test_owns_album(async_spotify_user_auth, scorpion_album_id):
    assert await async_spotify_user_auth.owns_albums(scorpion_album_id)


async def test_owns_albums(
    async_spotify_user_auth, scorpion_album_id, nothing_was_the_same_album_id
):
    assert await async_spotify_user_auth.owns_albums(
        [scorpion_album_id, nothing_was_the_same_album_id]
    )


async def test_delete_album(async_spotify_user_auth, scorpion_album_id):
    assert await async_spotify_user_auth.delete_albums(scorpion_album_id) is not None


async def test_delete_albums(
    async_spotify_user_auth, scorpion_album_id, nothing_was_the_same_album_id
):
    assert (
        await async_spotify_user_auth.delete_albums(
            [scorpion_album_id, nothing_was_the_same_album_id]
        )
        is not None
    )


async def test_album(
    async_spotify_user_auth, reise_reise_album_id, ritual_spirit_album_id
):
    assert await async_spotify_user_auth.albums(
        album_ids=[reise_reise_album_id, ritual_spirit_album_id]
    )


async def test_albums(async_spotify_user_auth, reise_reise_album_id):
    assert await async_spotify_user_auth.albums(reise_reise_album_id)
