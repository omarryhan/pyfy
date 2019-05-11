from aiohttp import ClientSession
import pytest

from pyfy.async_client import AsyncSpotify


def test_async_instantiates_empty():
    AsyncSpotify()
