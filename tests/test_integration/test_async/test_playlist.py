import pytest

from pyfy import AsyncSpotify as Spotify

pytestmark = pytest.mark.asyncio


async def test_user_playlists(user_creds_from_env, client_creds_from_env):
    c = Spotify(client_creds=client_creds_from_env, user_creds=user_creds_from_env)
    c.user_creds.user_id = None
    assert await c.user_playlists()


async def test_follow_playlist(async_spotify_user_auth, brian_eno_playlist_id):
    assert (
        await async_spotify_user_auth.follow_playlist(brian_eno_playlist_id) is not None
    )


async def test_follows_playlist(async_spotify_user_auth, brian_eno_playlist_id):
    assert (
        await async_spotify_user_auth.follows_playlist(brian_eno_playlist_id)
        is not None
    )


async def test_unfollow_playlist(async_spotify_user_auth, brian_eno_playlist_id):
    assert (
        await async_spotify_user_auth.unfollow_playlist(brian_eno_playlist_id)
        is not None
    )


async def test_create_playlist(async_spotify_user_auth, new_playlist_name):
    assert await async_spotify_user_auth.create_playlist(new_playlist_name) is not None


async def test_update_playlist(
    async_spotify_user_auth, new_playlist_id, new_playlist_name
):
    assert (
        await async_spotify_user_auth.update_playlist(
            new_playlist_id, "NEWNAMENOONECANTHINKOF"
        )
        is not None
    )
    assert (
        await async_spotify_user_auth.update_playlist(
            new_playlist_id, new_playlist_name
        )
        is not None
    )


async def test_add_playlist_tracks(
    async_spotify_user_auth, new_playlist_id, them_bones_track_id, gods_plan_track_id
):
    assert (
        await async_spotify_user_auth.add_playlist_tracks(
            new_playlist_id, [them_bones_track_id, gods_plan_track_id]
        )
        is not None
    )


async def test_playlist_tracks(
    async_spotify_user_auth, new_playlist_id, them_bones_track_id
):
    assert await async_spotify_user_auth.playlist_tracks(new_playlist_id)


async def test_reorder_playlist_track(
    async_spotify_user_auth, new_playlist_id, sonne_track_id
):
    assert (
        await async_spotify_user_auth.add_playlist_tracks(
            new_playlist_id, sonne_track_id
        )
        is not None
    )
    assert (
        await async_spotify_user_auth.reorder_playlist_track(
            new_playlist_id, range_start=1, insert_before=0
        )
        is not None
    )


async def test_delete_playlist_tracks(
    async_spotify_user_auth, new_playlist_id, gods_plan_track_id, them_bones_track_id
):
    assert (
        await async_spotify_user_auth.delete_playlist_tracks(
            new_playlist_id,
            [
                {"id": gods_plan_track_id, "positions": 0},
                {"id": them_bones_track_id, "positions": 1},
            ],
        )
        is not None
    )


async def test_delete_playlist(async_spotify_user_auth, new_playlist_id):
    assert await async_spotify_user_auth.delete_playlist(new_playlist_id) is not None
