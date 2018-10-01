from pyfy import Client


def test_user_playlists(user_creds_from_env):
    c = Client(user_creds=user_creds_from_env, ensure_user_auth=True)
    c.user_creds.user_id = None
    assert c.user_platlists
