def test_me(spotify_user_auth):
    assert spotify_user_auth.me()


def test_user_profile(spotify_user_auth, john_smith_user_id):
    assert spotify_user_auth.user_profile(john_smith_user_id)
