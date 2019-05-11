import pytest

pytestmark = pytest.mark.asyncio


async def test_category_soul(async_spotify_user_auth):
    assert await async_spotify_user_auth.category("soul")


async def test_category_sleep(async_spotify_user_auth):
    assert await async_spotify_user_auth.category("sleep")


async def test_category_jazz(async_spotify_user_auth):
    assert await async_spotify_user_auth.category("jazz")


async def test_categories(async_spotify_user_auth):
    assert await async_spotify_user_auth.categories()


async def test_categories_usa(async_spotify_user_auth):
    assert await async_spotify_user_auth.categories(country="US")


async def test_category_playlist(async_spotify_user_auth):
    assert await async_spotify_user_auth.category_playlist("jazz")


async def test_featured_playlists(async_spotify_user_auth):
    assert await async_spotify_user_auth.featured_playlists()


async def test_new_releases(async_spotify_user_auth):
    assert await async_spotify_user_auth.new_releases()


async def test_recommendations(async_spotify_user_auth):
    assert await async_spotify_user_auth.recommendations(
        market="US",
        seed_tracks="0c6xIDDpzE81m2q797ordA",
        min_energy=0.4,
        min_popularity=50,
    )


async def test_track_audio_analysis(async_spotify_user_auth, pound_cake_track_id):
    await async_spotify_user_auth.track_audio_analysis(pound_cake_track_id)


async def test_track_audio_feature(async_spotify_user_auth, pound_cake_track_id):
    await async_spotify_user_auth.tracks_audio_features(pound_cake_track_id)


async def test_tracks_audio_features(
    async_spotify_user_auth, pound_cake_track_id, gods_plan_track_id
):
    await async_spotify_user_auth.tracks_audio_features(
        [pound_cake_track_id, gods_plan_track_id]
    )


async def test_search(async_spotify_user_auth):
    await async_spotify_user_auth.search("where's the revolution")


async def test_available_genre_seeds(async_spotify_user_auth):
    assert await async_spotify_user_auth.available_genre_seeds()
