import pytest

pytestmark = pytest.mark.asyncio

#
# def test_devices(async_spotify_user_auth, event_loop):
#    assert event_loop.run_until_complete(async_spotify_user_auth.devices())
#
async def test_devices(async_spotify_user_auth):
    assert await async_spotify_user_auth.devices()


async def test_recently_played_tracks(async_spotify_user_auth):
    assert await async_spotify_user_auth.recently_played_tracks()


async def test_play_album(async_spotify_user_auth, reise_reise_album_id):
    assert await async_spotify_user_auth.play(album_id=reise_reise_album_id) is not None
    assert await async_spotify_user_auth.pause() is not None


async def test_play_single_track_id(async_spotify_user_auth, them_bones_track_id):
    assert await async_spotify_user_auth.play(track_ids=them_bones_track_id) is not None
    assert await async_spotify_user_auth.pause() is not None


async def test_play_track_ids(
    async_spotify_user_auth, them_bones_track_id, cover_me_track_id
):
    assert (
        await async_spotify_user_auth.play(
            track_ids=[them_bones_track_id, cover_me_track_id]
        )
        is not None
    )
    assert await async_spotify_user_auth.pause() is not None


async def test_play_artist(async_spotify_user_auth, depeche_mode_artist_id):
    assert (
        await async_spotify_user_auth.play(artist_id=depeche_mode_artist_id) is not None
    )
    assert await async_spotify_user_auth.pause() is not None


async def test_play_with_no_args(async_spotify_user_auth):
    assert await async_spotify_user_auth.play() is not None


async def test_currently_playing(async_spotify_user_auth):
    assert await async_spotify_user_auth.currently_playing()


async def test_currently_playing_info(async_spotify_user_auth):
    assert await async_spotify_user_auth.currently_playing_info()


async def test_previous(async_spotify_user_auth):
    assert await async_spotify_user_auth.previous() is not None


async def test_next(async_spotify_user_auth):
    assert await async_spotify_user_auth.next() is not None


async def test_repeat(async_spotify_user_auth):
    assert await async_spotify_user_auth.repeat() is not None


async def test_shuffle(async_spotify_user_auth):
    assert await async_spotify_user_auth.shuffle() is not None


async def test_seek(async_spotify_user_auth):
    assert await async_spotify_user_auth.seek(10000) is not None  # 10 seconds


async def test_volume(async_spotify_user_auth):
    assert await async_spotify_user_auth.volume(72) is not None
    assert await async_spotify_user_auth.volume(32) is not None


async def test_pause(async_spotify_user_auth):
    assert await async_spotify_user_auth.pause() is not None
