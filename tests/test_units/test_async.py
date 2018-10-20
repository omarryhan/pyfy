from pyfy.async_client import AsyncSpotify


def test_async_instantiates_empty():
    assert AsyncSpotify()

def test_session_exists():
    spt = AsyncSpotify()
    assert spt._session is not None

#def test_devices(spotify_user_auth):
#    assert spotify_user_auth.devices()
#
#def test_play(spotify_user_auth):
#    assert spotify_user_auth.play() is not None