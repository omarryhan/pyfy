import os
import pytest
import requests

from pyfy import ALL_SCOPES, AuthError, ClientCreds

def test_integration_tests_discovered():
    assert True


def test_valid_oauth_uri(spotify, client_creds_from_env):
    # Assumes valid spotify id and "valid" spotify secret
    spotify.client_creds = client_creds_from_env
    assert spotify.oauth_uri
    assert requests.get(spotify.oauth_uri).status_code == 200


def test_all_scopes_are_valid(spotify, client_creds_from_env):
    spotify.client_creds = client_creds_from_env
    spotify.client_creds.scopes = ALL_SCOPES
    assert spotify.oauth_uri
    assert requests.get(spotify.oauth_uri).status_code == 200


def test_client_credentials_oauth(spotify, client_creds_from_env):
    spotify.client_creds = client_creds_from_env
    spotify.authorize_client_creds()


def test_client_credentials_oauth_invalid(spotify, client_creds_from_env):
    spotify.client_creds = client_creds_from_env
    spotify.client_creds.client_id = 'BAD_CLIENT_ID'
    with pytest.raises(AuthError) as e:
        spotify.authorize_client_creds()


def test_client_credentials_oauth_is_authorized(spotify, client_creds_from_env):
    # https://developer.spotify.com/documentation/web-api/reference/browse/get-list-categories/
    spotify.client_creds = client_creds_from_env
    spotify.authorize_client_creds()
    assert spotify.is_active
    assert spotify.categories()


def test_client_credentials_refresh(spotify, client_creds_from_env):
    assert os.environ['SPOTIFY_CLIENT_ID']
    assert client_creds_from_env.client_id
    spotify.client_creds = client_creds_from_env
    spotify.authorize_client_creds()
    spotify._refresh_token()
    initial_client_access = spotify.client_creds.access_token
    spotify._refresh_token()
    refreshed_client_access = spotify.client_creds.access_token
    assert initial_client_access != refreshed_client_access
