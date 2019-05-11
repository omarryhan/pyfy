def test_followed_artists(spotify_user_auth):
    assert spotify_user_auth.followed_artists() is not None


def test_follow_artist(spotify_user_auth, test_artist_id):
    assert spotify_user_auth.follow_artists(test_artist_id) is not None


def test_follow_artists(spotify_user_auth, test_artist_id, testing_funny_artist_id):
    assert (
        spotify_user_auth.follow_artists([test_artist_id, testing_funny_artist_id])
        is not None
    )


def test_follows_artist(spotify_user_auth, test_artist_id):
    assert spotify_user_auth.follows_artists(test_artist_id) is not None


def test_follows_artists(spotify_user_auth, test_artist_id, testing_funny_artist_id):
    assert (
        spotify_user_auth.follow_artists([test_artist_id, testing_funny_artist_id])
        is not None
    )


def test_unfollow_artist(spotify_user_auth, test_artist_id):
    assert spotify_user_auth.unfollow_artists(test_artist_id) is not None


def test_unfollow_artists(spotify_user_auth, test_artist_id, testing_funny_artist_id):
    assert (
        spotify_user_auth.unfollow_artists([test_artist_id, testing_funny_artist_id])
        is not None
    )


def test_artist(spotify_user_auth, depeche_mode_artist_id):
    assert spotify_user_auth.artists(depeche_mode_artist_id)


def test_artists(spotify_user_auth, rammstein_artist_id, depeche_mode_artist_id):
    assert spotify_user_auth.artists([rammstein_artist_id, depeche_mode_artist_id])


def test_artist_related_artists(spotify_user_auth, depeche_mode_artist_id):
    assert spotify_user_auth.artist_related_artists(depeche_mode_artist_id)
