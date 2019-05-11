import pytest
from pytest import fixture

from pyfy import Spotify, ClientCreds, UserCreds, AsyncSpotify
from pyfy.utils import _safe_getitem


@fixture(scope="function")
def spotify():
    yield Spotify()


@fixture(scope="function")
def client_creds_from_env_session():
    client = ClientCreds()
    client.load_from_env()
    client.show_dialog = "true"
    yield client


@fixture(scope="function")
def user_creds_from_env_session():
    user = UserCreds()
    user.load_from_env()
    yield user


@fixture(scope="function")
def client_creds_from_env():
    client = ClientCreds()
    client.load_from_env()
    client.show_dialog = "true"
    yield client


@fixture(scope="function")
def user_creds_from_env():
    user = UserCreds()
    user.load_from_env()
    if not user.access_token:
        raise AttributeError("User must have an access token for some tests to run")
    yield user


@fixture(scope="session")
def spotify_user_auth():
    spotify = Spotify()
    user_creds = UserCreds()
    client_creds = ClientCreds()
    client_creds.load_from_env()
    user_creds.load_from_env()
    spotify.client_creds = client_creds
    spotify.user_creds = user_creds
    spotify._caller = spotify.user_creds
    yield spotify


@fixture(scope="session")
def async_spotify_user_auth():
    spotify = AsyncSpotify()
    user_creds = UserCreds()
    client_creds = ClientCreds()
    client_creds.load_from_env()
    user_creds.load_from_env()
    spotify.client_creds = client_creds
    spotify.user_creds = user_creds
    spotify._caller = spotify.user_creds
    yield spotify


@fixture(scope="function")
def spotify_client_auth():
    spotify = Spotify()
    client_creds = ClientCreds()
    client_creds.load_from_env()
    spotify.client_creds = client_creds
    yield spotify


@fixture(scope="function")
def async_spotify_client_auth():
    spotify = AsyncSpotify()
    client_creds = ClientCreds()
    client_creds.load_from_env()
    spotify.client_creds = client_creds
    yield spotify


# ================================================================== Stubs ===================================================================#


@fixture
def me_stub():
    return {
        "birthdate": "1900-01-01",
        "country": "US",
        "display_name": "someone",
        "email": "someone@gmail.com",
        "external_urls": {"spotify": "https://open.spotify.com/user/asdmiapdsmoand"},
        "followers": {"href": "null", "total": 8},
        "href": "https://api.spotify.com/v1/users/asdonaisdnaiusdnai",
        "id": "asdoijoijasdijaojsd",
        "images": [],
        "product": "premium",
        "type": "user",
        "uri": "spotify:user:oofnvasdasyduj2bhasdasdasd",
    }


@fixture
def cover_me_track_id():
    return "18Om2WhO0dlFHKqcMcpxxA"


@fixture
def in_your_room_track_id():
    return "60hzrNGckC5cho1JkmyVm4"


@fixture
def voodoo_in_my_blood_track_id():
    return "0DRe2MeIAT5Bf1kOhRPJ4H"


@fixture
def sonne_track_id():
    return "6VS4C2HnOQPivcjcAAlUMj"


@fixture
def rammstein_artist_id():
    return "6wWVKhxIU2cEi0K81v7HvP"


@fixture
def depeche_mode_artist_id():
    return "762310PdDnwsDxAQxzQkfX"


@fixture
def massive_attack_artist_id():
    return "6FXMGgJwohJLUSr5nVlf9X"


@fixture
def songs_of_faith_and_devotion_album_id():
    return "6x7S6u9Cx2S0JD48nPsavE"


@fixture
def far_and_off_album_id():
    return "2EmxGavHNvex1vNWfoq9yI"


@fixture
def reise_reise_album_id():
    return "74ydDCcXTco741y42ceRJ5"


@fixture
def ritual_spirit_album_id():
    return "6KHhT15M6l7cgaPZamEpM3"


@fixture
def biosphere_public_playlist_id():
    return "37i9dQZF1DZ06evO1ov2lQ"


@fixture
def aes_dana_public_playlist_id():
    return "37i9dQZF1DZ06evO3LdcHu"


@fixture
def metal_essentials_playlist_id():
    return "37i9dQZF1DWWOaP4H0w5b0"


@fixture
def brian_eno_playlist_id():
    return "22dXpXoyZjk9bhZABaIDOq"


@fixture
def the_metal_podcast_id():
    return "0O1qo57pGLPvk5BcK7HXk6"


@fixture
def ambient_podcast_id():
    return "279ykQVh10jwcXuaikY82k"


@fixture
def john_smith_user_id():
    return "1235168545"


@fixture
def spotify_test_user_id():
    return "asbmkbqbyrh657mrrzx4c94dd"


@fixture
def test_artist_id():
    return "5OV9PowyUJwaXMsLC9GlEE"


@fixture
def testing_funny_artist_id():  # That's an actual band (testing funny)
    return "1X8mNJTyrSeJ6XrTwOfC1u"


@fixture
def gods_plan_track_id():
    return "6DCZcSspjsKoFjzjrWoCdn"


@fixture
def pound_cake_track_id():
    return "4RI9eX7jNcdaQOJifn7t6z"


@fixture
def nothing_was_the_same_album_id():
    return "2ZUFSbIkmFkGag000RWOpA"


@fixture
def scorpion_album_id():
    return "1ATL5GLyefJaxhQzSPVrLX"


@fixture
def them_bones_track_id():
    return "4A065x9kJt955eGVqf813g"


#### misc


@fixture()
def new_playlist_name():
    return "TEST_PLAYLIST"


@fixture(scope="function")
def new_playlist_id(spotify_user_auth, new_playlist_name):
    for playlist in spotify_user_auth.user_playlists()["items"]:
        if _safe_getitem(playlist, "name") == new_playlist_name:
            return _safe_getitem(playlist, "id")
