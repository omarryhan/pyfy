def test_devices(spotify_user_auth):
    assert spotify_user_auth.devices()


def test_recently_played_tracks(spotify_user_auth):
    assert spotify_user_auth.recently_played_tracks()


def test_play(spotify_user_auth, reise_reise_album_id):
    assert spotify_user_auth.play(reise_reise_album_id, "album") is not None


def test_pause(spotify_user_auth):
    assert spotify_user_auth.pause() is not None


def test_play(spotify_user_auth, them_bones_track_id):
    assert spotify_user_auth.play(them_bones_track_id, "artist") is not None


def test_pause(spotify_user_auth):
    assert spotify_user_auth.pause() is not None


def test_play(spotify_user_auth, depeche_mode_artist_id):
    assert spotify_user_auth.play(depeche_mode_artist_id) is not None


def test_pause(spotify_user_auth):
    assert spotify_user_auth.pause() is not None


def test_play(spotify_user_auth):
    assert spotify_user_auth.play() is not None


def test_currently_playing(spotify_user_auth):
    assert spotify_user_auth.currently_playing()


def test_currently_playing_info(spotify_user_auth):
    assert spotify_user_auth.currently_playing_info()


def test_previous(spotify_user_auth):
    assert spotify_user_auth.previous() is not None


def test_next(spotify_user_auth):
    assert spotify_user_auth.next() is not None


def test_repeat(spotify_user_auth):
    assert spotify_user_auth.repeat() is not None


def test_shuffle(spotify_user_auth):
    assert spotify_user_auth.shuffle() is not None


def test_seek(spotify_user_auth):
    assert spotify_user_auth.seek(10000) is not None  # 10 seconds


def test_volume(spotify_user_auth):
    assert spotify_user_auth.volume(72) is not None
    assert spotify_user_auth.volume(32) is not None


def test_pause(spotify_user_auth):
    assert spotify_user_auth.pause() is not None
