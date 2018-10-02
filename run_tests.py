import os
import pytest
try:
    from spt_keys import KEYS
except:
    from spt_keys_template import KEYS


def export_keys():
    for k, v in KEYS.items():
        if v:
            os.environ[k] = v
            print("export " + k + "=" + v)


def run():
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
    access_token = os.getenv('SPOTIFY_ACCESS_TOKEN')
    redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI')
    test_integration = os.getenv('PYFY_TEST_INTEGRATION')

    if client_id and client_secret and access_token and redirect_uri and test_integration == 'true':  # Run unit tests then integration tests
        print('Running unit tests followed by integration tests')
        pytest.main(['-vv', '-s', '--cov', 'pyfy/', 'tests/test_units/', 'tests/test_integration/'])
    else:
        print('Running unit tests')
        pytest.main(['-vv', '-s', '--cov', 'pyfy/', 'tests/test_units/'])


if __name__ == '__main__':
    export_keys()
    run()
