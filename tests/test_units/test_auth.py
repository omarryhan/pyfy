from pyfy import AsyncSpotify, Spotify, ClientCreds
import pytest


def test_oauth_uri_raises_deprecation_warning():
    creds = ClientCreds(
        client_id="asdasdasdasdads",
        client_secret="asdasdasdasdasd",
        scopes=["asdasd", "asdasd"],
        redirect_uri="asdasdasdasd",
    )
    sync = Spotify(client_creds=creds)
    async_ = AsyncSpotify(client_creds=creds)

    with pytest.warns(DeprecationWarning):
        sync.oauth_uri

    with pytest.warns(DeprecationWarning):
        async_.oauth_uri
