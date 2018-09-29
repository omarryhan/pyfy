import pytest
from pytest import fixture

from pyfy import Client, ClientCredentials, UserCredentials

@fixture(scope='session')
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
    yield user
