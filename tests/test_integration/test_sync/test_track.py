def test_save_track(spotify_user_auth, gods_plan_track_id):
    assert spotify_user_auth.save_tracks(gods_plan_track_id) is not None


def test_save_tracks(spotify_user_auth, gods_plan_track_id, pound_cake_track_id):
    assert (
        spotify_user_auth.save_tracks([gods_plan_track_id, pound_cake_track_id])
        is not None
    )


def test_owns_track(spotify_user_auth, pound_cake_track_id):
    assert spotify_user_auth.owns_tracks(pound_cake_track_id)


def test_owns_tracks(spotify_user_auth, pound_cake_track_id, gods_plan_track_id):
    assert spotify_user_auth.owns_tracks([pound_cake_track_id, gods_plan_track_id])


def test_delete_track(spotify_user_auth, pound_cake_track_id):
    assert spotify_user_auth.delete_tracks(pound_cake_track_id) is not None


def test_delete_tracks(spotify_user_auth, pound_cake_track_id, gods_plan_track_id):
    assert (
        spotify_user_auth.delete_tracks([pound_cake_track_id, gods_plan_track_id])
        is not None
    )


def test_track(spotify_user_auth, sonne_track_id):
    assert spotify_user_auth.tracks(sonne_track_id)


def test_tracks(spotify_user_auth, sonne_track_id, in_your_room_track_id):
    assert spotify_user_auth.tracks([sonne_track_id, in_your_room_track_id])
