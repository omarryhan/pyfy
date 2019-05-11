import pytest

pytestmark = pytest.mark.asyncio


async def test_user_top_artists(async_spotify_user_auth):
    assert await async_spotify_user_auth.user_top_artists()


async def test_artist_albums(async_spotify_user_auth, depeche_mode_artist_id):
    assert await async_spotify_user_auth.artist_albums(depeche_mode_artist_id)


async def test_album_tracks(async_spotify_user_auth, reise_reise_album_id):
    assert await async_spotify_user_auth.album_tracks(reise_reise_album_id)


async def test_artist_top_tracks(async_spotify_user_auth, depeche_mode_artist_id):
    assert await async_spotify_user_auth.artist_top_tracks(
        depeche_mode_artist_id, country="US"
    )


#                                                                       #
# TODO: Write seperate unit tests for the get_key_recursively_method()  #
#                                                                       #


async def test_next_search(async_spotify_user_auth):
    result = await async_spotify_user_auth.search("love", "track", limit=2)
    assert len(result) > 0
    next_ = await async_spotify_user_auth.next_page(result)
    assert len(next_) > 0
    next_2 = await async_spotify_user_auth.next_page(next_)
    assert next_ != next_2
    assert len(next_2) > 0


async def test_previous_search(async_spotify_user_auth):
    result = await async_spotify_user_auth.search("stars", "track", limit=2)
    assert len(result) > 0
    next_ = await async_spotify_user_auth.next_page(result)
    next_2 = await async_spotify_user_auth.next_page(next_)
    previous = await async_spotify_user_auth.previous_page(next_2)
    assert len(previous) > 0
    assert previous == next_
    assert len(previous) > 0


async def test_next_featured_playlists(async_spotify_user_auth):
    result = await async_spotify_user_auth.featured_playlists(limit=2)
    assert len(result) > 0
    next_ = await async_spotify_user_auth.next_page(result)
    assert len(next_) > 0


async def test_next_recently_played_tracks(async_spotify_user_auth):
    result = await async_spotify_user_auth.recently_played_tracks(limit=2)
    assert len(result) > 0
    next_ = await async_spotify_user_auth.next_page(result)
    assert len(next_) > 0


async def test_next_user_albums(async_spotify_user_auth):
    result = await async_spotify_user_auth.user_albums(limit=2)
    assert len(result) > 0
    next_ = await async_spotify_user_auth.next_page(result)
    assert len(next_) > 0
