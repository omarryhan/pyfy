from pyfy import Spotify


def test_follow_user(spotify_user_auth, john_smith_user_id):
    assert spotify_user_auth.follow_users(john_smith_user_id) is not None


def test_follow_users(spotify_user_auth, john_smith_user_id, spotify_test_user_id):
    assert (
        spotify_user_auth.follow_users([john_smith_user_id, spotify_test_user_id])
        is not None
    )


def test_follows_user(spotify_user_auth, john_smith_user_id):
    assert spotify_user_auth.follows_users(john_smith_user_id) is not None


def test_follows_users(spotify_user_auth, john_smith_user_id, spotify_test_user_id):
    assert (
        spotify_user_auth.follows_users([john_smith_user_id, spotify_test_user_id])
        is not None
    )


def test_unfollow_user(spotify_user_auth, john_smith_user_id):
    assert spotify_user_auth.unfollow_users(john_smith_user_id) is not None


def test_unfollow_users(spotify_user_auth, john_smith_user_id, spotify_test_user_id):
    assert (
        spotify_user_auth.unfollow_users([john_smith_user_id, spotify_test_user_id])
        is not None
    )


def test_user_top_tracks(spotify_user_auth):
    assert spotify_user_auth.user_top_tracks()
