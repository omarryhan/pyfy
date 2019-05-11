import os, sys
import pytest


def run():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    access_token = os.getenv("SPOTIFY_ACCESS_TOKEN")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")
    test_integration_sync = os.getenv("PYFY_TEST_INTEGRATION_SYNC")
    test_integration_async = os.getenv("PYFY_TEST_INTEGRATION_ASYNC")

    if (
        client_id
        and client_secret
        and access_token
        and redirect_uri
        and test_integration_sync == "true"
        and test_integration_async == "true"
    ):  # Run unit tests then integration tests
        print("Running unit tests followed by integration tests")
        exit_code = pytest.main(
            [
                "-v",
                "-s",
                #'--maxfail=2',
                #'--fulltrace',
                "--cov",
                "pyfy/",
                "tests/test_units/",
                "tests/test_integration/test_async/",
                "tests/test_integration/test_sync/",
            ]
        )
    elif (
        client_id
        and client_secret
        and access_token
        and redirect_uri
        and test_integration_sync == "true"
        and test_integration_async != "true"
    ):  # Run unit tests then integration tests
        print("Running unit tests followed by synchronous integration tests")
        exit_code = pytest.main(
            [
                "-v",
                "-s",
                "--cov",
                "pyfy/",
                "tests/test_units/",
                "tests/test_integration/test_sync/",
            ]
        )
    elif (
        client_id
        and client_secret
        and access_token
        and redirect_uri
        and test_integration_sync != "true"
        and test_integration_async == "true"
    ):  # Run unit tests then integration tests
        print("Running unit tests followed by asynchronous integration tests")
        exit_code = pytest.main(
            [
                "-v",
                "-s",
                "--cov",
                "pyfy/",
                "tests/test_units/",
                "tests/test_integration/test_async/",
            ]
        )
    else:
        print("Running unit tests")
        exit_code = pytest.main(["-v", "-s", "--cov", "pyfy/", "tests/test_units/"])

    sys.exit(exit_code)


if __name__ == "__main__":
    run()
