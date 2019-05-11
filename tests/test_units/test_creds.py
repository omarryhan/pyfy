import datetime

import pytest

from pyfy import ClientCreds, UserCreds
from pyfy.creds import _Creds


def test_creds_loaded_from_env(user_creds_from_env, client_creds_from_env):
    assert user_creds_from_env.access_token
    assert client_creds_from_env.client_id


def test_client_is_oauth_ready(client_creds_from_env):
    """ for successfull oauth authorization request, spotify requires: client-id, redirect-uri and scopes """
    assert client_creds_from_env.is_oauth_ready  # Should be ready out of the box


def test_client_is_not_oauth_ready_without_clientid(client_creds_from_env):
    client_creds_from_env.client_id = None
    assert (
        not client_creds_from_env.is_oauth_ready
    )  # Assert not ready without a clientID


def test_client_is_not_oauth_ready_without_scopes(client_creds_from_env):
    client_creds_from_env.scopes = None
    assert not client_creds_from_env.is_oauth_ready  # Assert not ready without scopes


def test_client_is_not_oauth_ready_without_redirect_uri(client_creds_from_env):
    client_creds_from_env.redirect_uri = None
    assert (
        not client_creds_from_env.is_oauth_ready
    )  # assert not ready when there's no redirect uri


def test_creds_pickle(user_creds_from_env):
    user_creds_from_env.pickle()
    user_creds_from_env._delete_pickle()


def test_creds_pickle_loads_data_properly(user_creds_from_env):
    user_creds_from_env.pickle()
    new_user_creds = UserCreds.unpickle()
    assert new_user_creds.__dict__ == user_creds_from_env.__dict__
    user_creds_from_env._delete_pickle()


def test_creds_json_flow(user_creds_from_env):
    user_creds_from_env.save_as_json()
    user_creds_from_env.load_from_json()
    user_creds_from_env._delete_json()


def test_creds_json_loads_data_properly(user_creds_from_env):
    user_creds_from_env.save_as_json()
    new_user_creds = UserCreds()
    new_user_creds.load_from_json()
    assert new_user_creds.__dict__ == user_creds_from_env.__dict__
    user_creds_from_env._delete_json()


def test_creds_is_not_instantiable():
    with pytest.raises(TypeError) as e:
        _Creds()


def access_is_expired(user_creds_from_env):
    user_creds_from_env.expiry = datetime.datetime.utcnow()
    assert user_creds_from_env.access_is_expired is True
    user_creds_from_env.expiry = datetime.datetime.utcnow() + datetime.timedelta(
        minutes=2
    )
    assert user_creds_from_env.access_is_expired is False
