import pytest
from pytest import fixture

from pyfy import Client

@fixture(scope='session')
def client():
    yield Client()