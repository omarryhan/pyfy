import pytest
from pytest import fixture

from pyfy import Client, ClientCredentials

@fixture(scope='session')
def client():
    yield Client()

@fixture(scope='session')
def client_creds_from_env():
    client_creds = ClientCredentials()
    client_creds.load_from_env()
    client_creds.show_dialog = 'true'
    yield client_creds
