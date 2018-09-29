import requests


def test_integration_tests_discovered():
    assert True


def test_valid_oauth_uri(client, client_creds_from_env):
    # Assumes valid client id and "valid" client secret
    client.client_creds = client_creds_from_env
    assert client.oauth_uri
    assert requests.get(client.oauth_uri).status_code == 200
