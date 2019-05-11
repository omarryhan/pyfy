import os
import pytest
import requests

from pyfy import ALL_SCOPES, AuthError, ClientCreds


def test_all_scopes_are_valid(spotify_client_auth):
    assert spotify_client_auth.auth_uri()
    assert requests.get(spotify_client_auth.auth_uri()).status_code == 200


def test_client_credentials_oauth(spotify_client_auth):
    spotify_client_auth.authorize_client_creds()


def test_client_credentials_oauth_invalid(spotify_client_auth):
    spotify_client_auth.client_creds.client_id = "BAD_CLIENT_ID"
    with pytest.raises(AuthError) as e:
        spotify_client_auth.authorize_client_creds()


def test_client_credentials_oauth_is_authorized(spotify_client_auth):
    # https://developer.spotify.com/documentation/web-api/reference/browse/get-list-categories/
    spotify_client_auth.authorize_client_creds()
    assert spotify_client_auth.is_active
    assert spotify_client_auth.categories()


def test_client_credentials_refresh(spotify_client_auth):
    spotify_client_auth.authorize_client_creds()
    spotify_client_auth._refresh_token()
    initial_client_access = spotify_client_auth.client_creds.access_token
    spotify_client_auth._refresh_token()
    refreshed_client_access = spotify_client_auth.client_creds.access_token
    assert initial_client_access != refreshed_client_access
