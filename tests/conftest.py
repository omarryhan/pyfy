import pytest
from pytest import fixture

from pyfy import Client, ClientCredentials, UserCredentials

@fixture(scope='function')
def client():
    yield Client()

@fixture(scope='session')
def client_creds_from_env_session():
    client = ClientCredentials()
    client.load_from_env()
    client.show_dialog = 'true'
    yield client

@fixture(scope='session')
def user_creds_from_env_session():
    user = UserCredentials()
    user.load_from_env()
    yield user

@fixture(scope='function')
def client_creds_from_env():
    client = ClientCredentials()
    client.load_from_env()
    client.show_dialog = 'true'
    yield client

@fixture(scope='function')
def user_creds_from_env():
    user = UserCredentials()
    user.load_from_env()
    if not user.access_token:
        raise AttributeError('User must have an access token for some tests to run')
    yield user

@fixture(scope='function')
def client_user_auth():
    client = Client()
    user_creds = UserCredentials()
    client_creds = ClientCredentials()
    client_creds.load_from_env()
    user_creds.load_from_env()
    client.client_creds = client_creds
    client.user_creds = user_creds
    client._caller = client.user_creds
    yield client

@fixture(scope='function')
def client_client_auth():
    client = Client()
    user_creds = UserCredentials()
    client_creds = ClientCredentials()
    client_creds.load_from_env()
    user_creds.load_from_env()
    client.client_creds = client_creds
    client.user_creds = user_creds
    client._caller = client.user_creds
    yield client

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