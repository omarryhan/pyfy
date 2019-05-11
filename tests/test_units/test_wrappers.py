import json

import pytest
from requests import Response, Request

from pyfy.wrappers import (
    _dispatch_request,
    _inject_user_id,
    _default_to_locale,
    _set_and_get_me_attr_async,
    _set_and_get_me_attr_sync,
)

from pyfy import Spotify, UserCreds, AsyncSpotify


def test_and_get_me_attr_attr_exists():
    spt = Spotify()

    spt.user_creds = UserCreds()
    spt.user_creds.id = "id1234"

    assert _set_and_get_me_attr_sync(spt, "id") == "id1234"


@pytest.mark.asyncio
async def test_and_get_me_attr_attr_exists_async():
    spt = AsyncSpotify()

    spt.user_creds = UserCreds()
    spt.user_creds.id = "id1234"

    assert await _set_and_get_me_attr_async(spt, "id") == "id1234"


def test_inject_user_id():
    pass


def test_default_to_locale():
    pass


def test_dispatch_request():
    pass
