import pprint

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

def test_track_audio_analysis(spotify_user_auth, pound_cake_track_id):
    spotify_user_auth.track_audio_analysis(pound_cake_track_id)

def test_track_audio_feature(spotify_user_auth, pound_cake_track_id):
    spotify_user_auth.tracks_audio_features(pound_cake_track_id)

def test_tracks_audio_features(spotify_user_auth, pound_cake_track_id, gods_plan_track_id):
    spotify_user_auth.tracks_audio_features([pound_cake_track_id, gods_plan_track_id])

def test_search(spotify_user_auth):
    spotify_user_auth.search('where\'s the revolution')

'''
TODO: Write seperate unit tests for the get_key_recursively_method()
'''

def test_next_search(spotify_user_auth):
    result = spotify_user_auth.search('love', 'track', limit=2)
    assert len(result) > 0
    next_ = spotify_user_auth.next_page(result)
    assert len(next_) > 0
    next_2 = spotify_user_auth.next_page(next_)
    assert next_ != next_2
    assert len(next_2) > 0

def test_previous_search(spotify_user_auth):
    result = spotify_user_auth.search('stars', 'track', limit=2)
    assert len(result) > 0
    next_ = spotify_user_auth.next_page(result)
    next_2 = spotify_user_auth.next_page(next_)
    previous = spotify_user_auth.previous_page(next_2)
    assert len(previous) > 0
    assert previous == next_
    assert len(previous) > 0

def test_next_featured_playlists(spotify_user_auth):
    result = spotify_user_auth.featured_playlists(limit=2)
    assert len(result) > 0
    next_ = spotify_user_auth.next_page(result)
    assert len(next_) > 0

def test_next_recently_played_tracks(spotify_user_auth):
    result = spotify_user_auth.recently_played_tracks(limit=2)
    assert len(result) > 0
    next_ = spotify_user_auth.next_page(result)
    assert len(next_) > 0

def test_next_user_albums(spotify_user_auth):
    result = spotify_user_auth.user_albums(limit=2)
    assert len(result) > 0
    next_ = spotify_user_auth.next_page(result)
    assert len(next_) > 0