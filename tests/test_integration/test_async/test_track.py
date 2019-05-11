import pytest

pytestmark = pytest.mark.asyncio


async def test_save_track(async_spotify_user_auth, gods_plan_track_id):
    assert await async_spotify_user_auth.save_tracks(gods_plan_track_id) is not None


async def test_save_tracks(
    async_spotify_user_auth, gods_plan_track_id, pound_cake_track_id
):
    assert (
        await async_spotify_user_auth.save_tracks(
            [gods_plan_track_id, pound_cake_track_id]
        )
        is not None
    )


async def test_owns_track(async_spotify_user_auth, pound_cake_track_id):
    assert await async_spotify_user_auth.owns_tracks(pound_cake_track_id)


async def test_owns_tracks(
    async_spotify_user_auth, pound_cake_track_id, gods_plan_track_id
):
    assert await async_spotify_user_auth.owns_tracks(
        [pound_cake_track_id, gods_plan_track_id]
    )


async def test_delete_track(async_spotify_user_auth, pound_cake_track_id):
    assert await async_spotify_user_auth.delete_tracks(pound_cake_track_id) is not None


async def test_delete_tracks(
    async_spotify_user_auth, pound_cake_track_id, gods_plan_track_id
):
    assert (
        await async_spotify_user_auth.delete_tracks(
            [pound_cake_track_id, gods_plan_track_id]
        )
        is not None
    )


async def test_track(async_spotify_user_auth, sonne_track_id):
    assert await async_spotify_user_auth.tracks(sonne_track_id)


async def test_tracks(async_spotify_user_auth, sonne_track_id, in_your_room_track_id):
    assert await async_spotify_user_auth.tracks([sonne_track_id, in_your_room_track_id])
