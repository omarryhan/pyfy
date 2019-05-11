import asyncio
from inspect import iscoroutine

import pytest


@pytest.mark.asyncio
async def test_gather(async_spotify_user_auth):
    spt = async_spotify_user_auth

    results = await spt.gather(
        spt.search("concurrency", to_gather=True),
        spt.categories(to_gather=True),
        spt.search(
            "event loop", to_gather=True
        ),  # There's actually a song called: "event loop" by Mushroom Giant
        spt.search("Search Biosphere", to_gather=True),
    )

    for result in results:
        assert isinstance(result, dict)
        assert len(result) != 0


def test_gather_now(async_spotify_user_auth):
    spt = async_spotify_user_auth

    results = spt.gather_now(
        spt.search("concurrency", to_gather=True),
        spt.categories(to_gather=True),
        spt.search("event loop", to_gather=True),
        spt.search("Search Biosphere", to_gather=True),
    )

    for result in results:
        assert isinstance(result, dict)
        assert len(result) != 0
