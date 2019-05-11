import pytest
import os
import requests

from pyfy import AuthError


def test_valid_oauth_uri(async_spotify_client_auth):
    # Assumes valid spotify id and "valid" spotify secret
    assert async_spotify_client_auth.auth_uri()
    assert requests.get(async_spotify_client_auth.auth_uri()).status_code == 200


@pytest.mark.asyncio
async def test_bad_client_creds_raise_auth_error(async_spotify_client_auth):
    async_spotify_client_auth.client_creds.client_secret = "bad secret"
    with pytest.raises(AuthError):
        await async_spotify_client_auth.authorize_client_creds()


@pytest.mark.asyncio
async def test_client_authentication_async(async_spotify_client_auth):
    await async_spotify_client_auth.authorize_client_creds()


@pytest.mark.asyncio
async def test_client_credentials_is_active(async_spotify_client_auth):
    await async_spotify_client_auth.authorize_client_creds()
    assert await async_spotify_client_auth.is_active is True
    json_res = await async_spotify_client_auth.categories()
    assert isinstance(json_res, dict)


@pytest.mark.asyncio
async def test_client_credentials_refresh(
    async_spotify_client_auth, client_creds_from_env
):
    assert os.environ["SPOTIFY_CLIENT_ID"]
    assert client_creds_from_env.client_id
    async_spotify_client_auth.client_creds = client_creds_from_env
    await async_spotify_client_auth.authorize_client_creds()
    await async_spotify_client_auth._refresh_token()
    initial_client_access = async_spotify_client_auth.client_creds.access_token
    await async_spotify_client_auth._refresh_token()
    refreshed_client_access = async_spotify_client_auth.client_creds.access_token
    assert initial_client_access != refreshed_client_access
