from pyfy import Spotify, UserCreds
import pytest

def test_caller_defaults_to_user():
    u = UserCreds(access_token='asdasdasd')
    c = Spotify(user_creds=u)
    assert c._caller == c.user_creds

def test_client_instantiates_with_access_token():
    u = UserCreds()
    u.load_from_env()
    access_token = u.access_token
    spt = Spotify(access_token=access_token)
    assert spt.user_creds.access_token is not None
    assert spt.user_creds.refresh_token is None

    assert spt._caller == spt.user_creds

    assert not hasattr(spt, 'access_token')

def test_client_instantiates_with_user_creds():
    u = UserCreds()
    u.load_from_env()
    spt = Spotify(user_creds=u, ensure_user_auth=False)
    assert spt.user_creds.access_token is not None

    assert spt._caller == spt.user_creds

def test_client_raises_error_if_both_access_token_and_model():
    u = UserCreds()
    u.load_from_env()
    with pytest.raises(ValueError):
        Spotify(user_creds=u, access_token=u.access_token)
