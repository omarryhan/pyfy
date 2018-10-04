def test_categories_usa(spotify_user_auth):
    assert spotify_user_auth.categories(country='US')

def test_album(spotify_user_auth, reise_reise_album_id, ritual_spirit_album_id):
    assert spotify_user_auth.albums(album_ids=[reise_reise_album_id, ritual_spirit_album_id])

def test_albums(spotify_user_auth, reise_reise_album_id):
    assert spotify_user_auth.albums(reise_reise_album_id)
    assert spotify_user_auth.albums(reise_reise_album_id)

def test_track(spotify_user_auth, sonne_track_id):
    assert spotify_user_auth.tracks(sonne_track_id)

def test_tracks(spotify_user_auth, sonne_track_id, in_your_room_track_id):
    assert spotify_user_auth.tracks([sonne_track_id, in_your_room_track_id])

def test_artist(spotify_user_auth, depeche_mode_artist_id):
    assert spotify_user_auth.artists(depeche_mode_artist_id)

def test_artists(spotify_user_auth, rammstein_artist_id, depeche_mode_artist_id):
    assert spotify_user_auth.artists([rammstein_artist_id, depeche_mode_artist_id])

def test_album_tracks(spotify_user_auth, reise_reise_album_id):
    assert spotify_user_auth.album_tracks(reise_reise_album_id)

def test_artist_albums(spotify_user_auth, depeche_mode_artist_id):
    assert spotify_user_auth.artist_albums(depeche_mode_artist_id)

def test_artist_related_artists(spotify_user_auth, depeche_mode_artist_id):
    assert spotify_user_auth.artist_related_artists(depeche_mode_artist_id)

def test_artist_top_tracks(spotify_user_auth, depeche_mode_artist_id):
    assert spotify_user_auth.artist_top_tracks(depeche_mode_artist_id, country='US')

def test_available_genre_seeds(spotify_user_auth):
    assert spotify_user_auth.available_genre_seeds()

def test_category(spotify_user_auth):
    assert spotify_user_auth.category('sleep')
    assert spotify_user_auth.category('soul')
    assert spotify_user_auth.category('jazz')

def test_categories(spotify_user_auth):
    assert spotify_user_auth.categories()

def test_category_playlist(spotify_user_auth):
    assert spotify_user_auth.category_playlist('jazz')

def test_featured_playlists(spotify_user_auth):
    assert spotify_user_auth.featured_playlists()

def test_new_releases(spotify_user_auth):
    assert spotify_user_auth.new_releases()

def test_recommendations(spotify_user_auth):
    assert spotify_user_auth.recommendations(market='US', seed_tracks='0c6xIDDpzE81m2q797ordA', min_energy=0.4, min_popularity=50)
