def test_album(client_user_auth, reise_reise_album_id, ritual_spirit_album_id):
    assert client_user_auth.albums(album_ids=[reise_reise_album_id, ritual_spirit_album_id])

def test_albums(client_user_auth, reise_reise_album_id):
    assert client_user_auth.albums(reise_reise_album_id)

def test_track(client_user_auth, sonne_track_id):
    assert client_user_auth.tracks(sonne_track_id)

def test_tracks(client_user_auth, sonne_track_id, in_your_room_track_id):
    assert client_user_auth.tracks([sonne_track_id, in_your_room_track_id])

def test_artist(client_user_auth, depeche_mode_artist_id):
    assert client_user_auth.artists(depeche_mode_artist_id)

def test_artists(client_user_auth, rammstein_artist_id, depeche_mode_artist_id):
    assert client_user_auth.artists([rammstein_artist_id, depeche_mode_artist_id])

def test_album_tracks(client_user_auth, reise_reise_album_id):
    assert client_user_auth.album_tracks(reise_reise_album_id)

def test_artist_albums(client_user_auth, depeche_mode_artist_id):
    assert client_user_auth.artist_albums(depeche_mode_artist_id)

def test_artist_related_artists(client_user_auth, depeche_mode_artist_id):
    assert client_user_auth.artist_related_artists(depeche_mode_artist_id)

def test_artist_top_tracks(client_user_auth, depeche_mode_artist_id):
    assert client_user_auth.artist_top_tracks(depeche_mode_artist_id, country='US')

def test_available_genre_seeds(client_user_auth):
    assert client_user_auth.available_genre_seeds()

def test_category(client_user_auth):
    assert client_user_auth.category('sleep')
    assert client_user_auth.category('soul')
    assert client_user_auth.category('jazz')

def test_categories(client_user_auth):
    assert client_user_auth.categories()

def test_category_playlist(client_user_auth):
    assert client_user_auth.category_playlist('jazz')

def test_featured_playlists(client_user_auth):
    assert client_user_auth.featured_playlists()

def test_new_releases(client_user_auth):
    assert client_user_auth.new_releases()

def test_recommendations(client_user_auth):
    # Not working for me. Try here: https://developer.spotify.com/console/get-recommendations/
    #assert client_user_auth.recommendations(max_energy=1.0, min_energy=0.8)
    #assert client_user_auth.recommendations()
    assert True