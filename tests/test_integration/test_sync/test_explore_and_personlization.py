def test_category(spotify_user_auth):
    assert spotify_user_auth.category("sleep")
    assert spotify_user_auth.category("soul")
    assert spotify_user_auth.category("jazz")


def test_categories(spotify_user_auth):
    assert spotify_user_auth.categories()


def test_categories_usa(spotify_user_auth):
    assert spotify_user_auth.categories(country="US")


def test_category_playlist(spotify_user_auth):
    assert spotify_user_auth.category_playlist("jazz")


def test_featured_playlists(spotify_user_auth):
    assert spotify_user_auth.featured_playlists()


def test_new_releases(spotify_user_auth):
    assert spotify_user_auth.new_releases()


def test_recommendations(spotify_user_auth):
    assert spotify_user_auth.recommendations(
        market="US",
        seed_tracks="0c6xIDDpzE81m2q797ordA",
        min_energy=0.4,
        min_popularity=50,
    )


def test_track_audio_analysis(spotify_user_auth, pound_cake_track_id):
    spotify_user_auth.track_audio_analysis(pound_cake_track_id)


def test_track_audio_feature(spotify_user_auth, pound_cake_track_id):
    spotify_user_auth.tracks_audio_features(pound_cake_track_id)


def test_tracks_audio_features(
    spotify_user_auth, pound_cake_track_id, gods_plan_track_id
):
    spotify_user_auth.tracks_audio_features([pound_cake_track_id, gods_plan_track_id])


def test_search(spotify_user_auth):
    spotify_user_auth.search("where's the revolution")


def test_available_genre_seeds(spotify_user_auth):
    assert spotify_user_auth.available_genre_seeds()
