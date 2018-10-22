from aiohttp import ClientSession
import pytest

from pyfy.async_client import AsyncSpotify

def test_async_instantiates_empty():
    assert AsyncSpotify()

@pytest.mark.asyncio
async def test_session_exists():
    spt = AsyncSpotify()
    async with spt.Session() as sess:
        assert isinstance(sess, ClientSession)
