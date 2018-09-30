import pytest
import requests

from pyfy import ALL_SCOPES, AuthError


def test_integration_tests_discovered():
    assert True


def test_valid_oauth_uri(client, client_creds_from_env):
    # Assumes valid client id and "valid" client secret
    client.client_creds = client_creds_from_env
    assert client.oauth_uri
    assert requests.get(client.oauth_uri).status_code == 200


def test_all_scopes_are_valid(client, client_creds_from_env):
    client.client_creds = client_creds_from_env
    client.client_creds.scopes = ALL_SCOPES
    assert client.oauth_uri
    assert requests.get(client.oauth_uri).status_code == 200


def test_client_credentials_oauth(client, client_creds_from_env):
    client.authorize_client_creds()


def test_client_credentials_oauth_invalid(client, client_creds_from_env):
    client.client_creds = client_creds_from_env
    client.client_creds.client_id = 'BAD_CLIENT_ID'
    with pytest.raises(AuthError) as e:
        client.authorize_client_creds()


def test_client_credentials_oauth_can_get_tracks(client, client_creds_from_env):
    client.client_creds = client_creds_from_env
    client.authorize_client_creds()
    assert client.random_tracks
