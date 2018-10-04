from pyfy import Spotify, UserCreds

def test_caller_defaults_to_user():
    u = UserCreds(access_token='asdasdasd')
    c = Spotify(user_creds=u)
    assert c._caller == c.user_creds
