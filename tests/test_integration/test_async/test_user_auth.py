from pyfy import AsyncSpotify as Spotify, AuthError, ClientCreds
import pytest


pytestmark = pytest.mark.asyncio
## This submodule must test authentication without having a client credentials model set to the client.

empty_client_creds = ClientCreds()


async def test_user_is_authenticated_by_access_token(
    user_creds_from_env, client_creds_from_env
):
    """
    This will also work if you provide an empty client creds model. But when the access token eventually expires you'll need valid client creds to refresh it
    """
    spt = Spotify(client_creds=client_creds_from_env, user_creds=user_creds_from_env)
    await spt.populate_user_creds()


async def test_user_is_active(user_creds_from_env, client_creds_from_env):
    """
    This will also work if you provide an empty client creds model. But when the access token eventually expires you'll need valid client creds to refresh it
    """
    spt = Spotify(client_creds=client_creds_from_env, user_creds=user_creds_from_env)
    assert await spt.is_active is True


async def test_user_is_rejected_with_bad_access_token(
    user_creds_from_env, client_creds_from_env
):
    user_creds_from_env.access_token = "BAD_ACCESS_TOKEN"
    spt = Spotify(client_creds=client_creds_from_env, user_creds=user_creds_from_env)
    assert spt._caller == spt.user_creds
    with pytest.raises(AuthError):
        await spt._check_authorization()


async def test_authenticated_user_is_authorized(
    user_creds_from_env, client_creds_from_env
):
    spotify = Spotify(
        client_creds=client_creds_from_env, user_creds=user_creds_from_env
    )
    assert await spotify.me()


async def test_user_refresh_token(user_creds_from_env, client_creds_from_env):
    spotify = Spotify(
        client_creds=client_creds_from_env, user_creds=user_creds_from_env
    )
    await spotify.populate_user_creds()
    await spotify._refresh_token()
