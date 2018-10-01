import pytest
from pytest import fixture

from pyfy import Client, ClientCredentials, UserCredentials

@fixture(scope='function')
def client():
    yield Client()

@fixture(scope='session')
def client_creds_from_env_session():
    client = ClientCredentials()
    client.load_from_env()
    client.show_dialog = 'true'
    yield client

@fixture(scope='session')
def user_creds_from_env_session():
    user = UserCredentials()
    user.load_from_env()
    yield user

@fixture(scope='function')
def client_creds_from_env():
    client = ClientCredentials()
    client.load_from_env()
    client.show_dialog = 'true'
    yield client

@fixture(scope='function')
def user_creds_from_env():
    user = UserCredentials()
    user.load_from_env()
    if not user.access_token:
        raise AttributeError('User must have an access token for some tests to run')
    yield user

@fixture(scope='function')
def client_with_creds_from_env():
    client = Client()
    user_creds = UserCredentials()
    client_creds = ClientCredentials()
    client_creds.load_from_env()
    user_creds.load_from_env()
    client.client_creds = client_creds
    client.user_creds = user_creds
    yield client


@fixture
def reise_reise_album():
    return '74ydDCcXTco741y42ceRJ5'