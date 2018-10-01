def test_get_albums_with_id(client_with_creds_from_env, reise_reise_album):
    assert client_with_creds_from_env.get_album(reise_reise_album)
