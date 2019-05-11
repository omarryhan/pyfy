def test_user_top_artists(spotify_user_auth):
    assert spotify_user_auth.user_top_artists()


def test_artist_albums(spotify_user_auth, depeche_mode_artist_id):
    assert spotify_user_auth.artist_albums(depeche_mode_artist_id)


def test_album_tracks(spotify_user_auth, reise_reise_album_id):
    assert spotify_user_auth.album_tracks(reise_reise_album_id)


def test_artist_top_tracks(spotify_user_auth, depeche_mode_artist_id):
    assert spotify_user_auth.artist_top_tracks(depeche_mode_artist_id, country="US")


#                                                                       #
# TODO: Write seperate unit tests for the get_key_recursively_method()  #
#                                                                       #


def test_next_search(spotify_user_auth):
    result = spotify_user_auth.search("love", "track", limit=2)
    assert len(result) > 0
    next_ = spotify_user_auth.next_page(result)
    assert len(next_) > 0
    next_2 = spotify_user_auth.next_page(next_)
    assert next_ != next_2
    assert len(next_2) > 0


def test_previous_search(spotify_user_auth):
    result = spotify_user_auth.search("stars", "track", limit=2)
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
