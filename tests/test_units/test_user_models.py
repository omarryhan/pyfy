import pytest
from pyfy import ClientCredentials, UserCredentials


def test_creds_loaded_from_env(user_creds_from_env, client_creds_from_env):
    assert user_creds_from_env.access_token
    assert client_creds_from_env.client_id


def test_state_automatically_generated_if_none(user_creds_from_env):
    assert user_creds_from_env.state
    assert isinstance(user_creds_from_env.state, str)


def test_client_is_oauth_ready(client_creds_from_env):
    ''' for successfull oauth authorization request, spotify requires: client-id, redirect-uri and scopes '''
    assert client_creds_from_env.is_oauth_ready  # Should be ready out of the box


def test_client_is_not_oauth_ready_without_clientid(client_creds_from_env):
    client_creds_from_env.client_id = None
    assert not client_creds_from_env.is_oauth_ready  # Assert not ready without a clientID


def test_client_is_not_oauth_ready_without_scopes(client_creds_from_env):
    client_creds_from_env.scopes = None
    assert not client_creds_from_env.is_oauth_ready  # Assert not ready without scopes


def test_client_is_not_oauth_ready_without_redirect_uri(client_creds_from_env):
    client_creds_from_env.redirect_uri = None
    assert not client_creds_from_env.is_oauth_ready  # assert not ready when there's no redirect uri


def test_list_type_scopes_is_asserted():
    with pytest.raises(TypeError) as e:
        UserCredentials(scopes='a list')


def test_user_model_pickled_to_default_path(user_creds_from_env):
    user_creds_from_env.save_to_file()
    user_creds_from_env._delete_pickle()


def test_user_model_loaded_from_pickle_to_default_path(user_creds_from_env):
    user_creds_from_env.save_to_file()
    user_creds_from_env.load_from_file()    
    user_creds_from_env._delete_pickle()