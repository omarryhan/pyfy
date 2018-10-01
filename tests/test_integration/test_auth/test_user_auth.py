from pyfy import Client, AuthError, ClientCredentials
import pytest


## This must test authentication without having a client credentials model loaded to the client.
## Only User model loaded from developer console or by any other means

empty_client_creds = ClientCredentials()


def test_user_is_authenticated_by_access_token(user_creds_from_env, client_creds_from_env):
    '''
    This will also work if you provide an empty client creds model. But when the access token eventually expires you'll need valid client creds to refresh it
    '''
    Client(client_creds=client_creds_from_env, user_creds=user_creds_from_env, ensure_user_auth=True)


def test_user_is_rejected_with_bad_access_token(user_creds_from_env, client_creds_from_env):
    user_creds_from_env.access_token = 'BAD_ACCESS_TOKEN'
    with pytest.raises(AuthError):
        Client(client_creds=client_creds_from_env, user_creds=user_creds_from_env, ensure_user_auth=True)


def test_authenticated_user_is_authorized(user_creds_from_env, client_creds_from_env):
    client = Client(client_creds=client_creds_from_env, user_creds=user_creds_from_env, ensure_user_auth=True)
    assert client.me
