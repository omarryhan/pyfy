import pytest
from pytest import fixture

from pyfy import Spotify, ClientCreds, UserCreds

@fixture(scope='function')
def spotify():
    yield Spotify()

@fixture(scope='session')
def client_creds_from_env_session():
    client = ClientCreds()
    client.load_from_env()
    client.show_dialog = 'true'
    yield client

@fixture(scope='session')
def user_creds_from_env_session():
    user = UserCreds()
    user.load_from_env()
    yield user

@fixture(scope='function')
def client_creds_from_env():
    client = ClientCreds()
    client.load_from_env()
    client.show_dialog = 'true'
    yield client

@fixture(scope='function')
def user_creds_from_env():
    user = UserCreds()
    user.load_from_env()
    if not user.access_token:
        raise AttributeError('User must have an access token for some tests to run')
    yield user

@fixture(scope='function')
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

@fixture(scope='function')
def spotify_client_auth():
    spotify = Spotify()
    user_creds = UserCreds()
    client_creds = ClientCreds()
    client_creds.load_from_env()
    user_creds.load_from_env()
    spotify.client_creds = client_creds
    spotify.user_creds = user_creds
    spotify._caller = spotify.user_creds
    yield spotify

#================================================================== Stubs ===================================================================#

@fixture
def cover_me_track_id():
    return '18Om2WhO0dlFHKqcMcpxxA'

@fixture
def in_your_room_track_id():
    return '60hzrNGckC5cho1JkmyVm4'

@fixture
def voodoo_in_my_blood_track_id():
    return '0DRe2MeIAT5Bf1kOhRPJ4H'

@fixture
def sonne_track_id():
    return '6VS4C2HnOQPivcjcAAlUMj'

@fixture
def rammstein_artist_id():
    return '6wWVKhxIU2cEi0K81v7HvP'

@fixture
def depeche_mode_artist_id():
    return '762310PdDnwsDxAQxzQkfX'

@fixture
def massive_attack_artist_id():
    return '6FXMGgJwohJLUSr5nVlf9X'

@fixture
def songs_of_faith_and_devotion_album_id():
    return '6x7S6u9Cx2S0JD48nPsavE'

@fixture
def far_and_off_album_id():
    return '2EmxGavHNvex1vNWfoq9yI'

@fixture
def reise_reise_album_id():
    return '74ydDCcXTco741y42ceRJ5'

@fixture
def ritual_spirit_album_id():
    return '6KHhT15M6l7cgaPZamEpM3'

@fixture
def biosphere_public_playlist_id():
    return '37i9dQZF1DZ06evO1ov2lQ'

@fixture
def aes_dana_public_playlist_id():
    return '37i9dQZF1DZ06evO3LdcHu'