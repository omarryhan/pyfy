from pyfy import Spotify
from time import sleep

def test_follow_user(spotify_user_auth, john_smith_user_id):
    assert spotify_user_auth.follow_users(john_smith_user_id) is not None

def test_follow_users(spotify_user_auth, john_smith_user_id, spotify_test_user_id):
    assert spotify_user_auth.follow_users([john_smith_user_id, spotify_test_user_id]) is not None

def test_follows_user(spotify_user_auth, john_smith_user_id):
    assert spotify_user_auth.follows_users(john_smith_user_id) is not None

def test_follows_users(spotify_user_auth, john_smith_user_id, spotify_test_user_id):
    assert spotify_user_auth.follows_users([john_smith_user_id, spotify_test_user_id]) is not None

def test_unfollow_user(spotify_user_auth, john_smith_user_id):
    assert spotify_user_auth.unfollow_users(john_smith_user_id) is not None

def test_unfollow_users(spotify_user_auth, john_smith_user_id, spotify_test_user_id):
    assert spotify_user_auth.unfollow_users([john_smith_user_id, spotify_test_user_id]) is not None

################## Artists

def test_followed_artists(spotify_user_auth):
    assert spotify_user_auth.followed_artists() is not None

def test_follow_artist(spotify_user_auth, test_artist_id):
    assert spotify_user_auth.follow_artists(test_artist_id) is not None

def test_follow_artists(spotify_user_auth, test_artist_id, testing_funny_artist_id):
    assert spotify_user_auth.follow_artists([test_artist_id, testing_funny_artist_id]) is not None

def test_follows_artist(spotify_user_auth, test_artist_id):
    assert spotify_user_auth.follows_artists(test_artist_id) is not None

def test_follows_artists(spotify_user_auth, test_artist_id, testing_funny_artist_id):
    assert spotify_user_auth.follow_artists([test_artist_id, testing_funny_artist_id]) is not None

def test_unfollow_artist(spotify_user_auth, test_artist_id):
    assert spotify_user_auth.unfollow_artists(test_artist_id) is not None

def test_unfollow_artists(spotify_user_auth, test_artist_id, testing_funny_artist_id):
    assert spotify_user_auth.unfollow_artists([test_artist_id, testing_funny_artist_id]) is not None

########## PLAYLISTS

def test_user_playlists(user_creds_from_env, client_creds_from_env):
    c = Spotify(client_creds=client_creds_from_env, user_creds=user_creds_from_env, ensure_user_auth=True)
    c.user_creds.user_id = None
    assert c.user_playlists()

def test_follow_playlist(spotify_user_auth, brian_eno_playlist_id):
    assert spotify_user_auth.follow_playlist(brian_eno_playlist_id) is not None

def test_follows_playlist(spotify_user_auth, brian_eno_playlist_id):
    assert spotify_user_auth.follows_playlist(brian_eno_playlist_id) is not None

def test_unfollow_playlist(spotify_user_auth, brian_eno_playlist_id):
    assert spotify_user_auth.unfollow_playlist(brian_eno_playlist_id) is not None


####### TRACKS

def test_save_track(spotify_user_auth, gods_plan_track_id):
    assert spotify_user_auth.save_tracks(gods_plan_track_id) is not None

def test_save_tracks(spotify_user_auth, gods_plan_track_id, pound_cake_track_id):
    assert spotify_user_auth.save_tracks([gods_plan_track_id, pound_cake_track_id]) is not None

def test_owns_track(spotify_user_auth, pound_cake_track_id):
    assert spotify_user_auth.owns_tracks(pound_cake_track_id)

def test_owns_tracks(spotify_user_auth, pound_cake_track_id, gods_plan_track_id):
    assert spotify_user_auth.owns_tracks([pound_cake_track_id, gods_plan_track_id])

def test_delete_track(spotify_user_auth, pound_cake_track_id):
    assert spotify_user_auth.delete_tracks(pound_cake_track_id) is not None

def test_delete_tracks(spotify_user_auth, pound_cake_track_id, gods_plan_track_id):
    assert spotify_user_auth.delete_tracks([pound_cake_track_id, gods_plan_track_id]) is not None

######## Albums

def test_save_album(spotify_user_auth, nothing_was_the_same_album_id):
    assert spotify_user_auth.save_albums(nothing_was_the_same_album_id) is not None

def test_save_albums(spotify_user_auth, scorpion_album_id, nothing_was_the_same_album_id):
    assert spotify_user_auth.save_albums([scorpion_album_id, nothing_was_the_same_album_id]) is not None

def test_owns_album(spotify_user_auth, scorpion_album_id):
    assert spotify_user_auth.owns_albums(scorpion_album_id)

def test_owns_albums(spotify_user_auth, scorpion_album_id, nothing_was_the_same_album_id):
    assert spotify_user_auth.owns_albums([scorpion_album_id, nothing_was_the_same_album_id])

def test_delete_album(spotify_user_auth, scorpion_album_id):
    assert spotify_user_auth.delete_albums(scorpion_album_id) is not None

def test_delete_albums(spotify_user_auth, scorpion_album_id, nothing_was_the_same_album_id):
    assert spotify_user_auth.delete_albums([scorpion_album_id, nothing_was_the_same_album_id]) is not None

####### top

def test_user_top_tracks(spotify_user_auth):
    assert spotify_user_auth.user_top_tracks()

def test_user_top_artists(spotify_user_auth):
    assert spotify_user_auth.user_top_artists()

###### player

def test_devices(spotify_user_auth):
    assert spotify_user_auth.devices()

def test_recently_played_tracks(spotify_user_auth):
    assert spotify_user_auth.recently_played_tracks()

def test_play(spotify_user_auth, reise_reise_album_id):
    assert spotify_user_auth.play(reise_reise_album_id, 'album') is not None

def test_pause(spotify_user_auth):
    assert spotify_user_auth.pause() is not None

def test_play(spotify_user_auth, them_bones_track_id):
    assert spotify_user_auth.play(them_bones_track_id, 'artist') is not None

def test_pause(spotify_user_auth):
    assert spotify_user_auth.pause() is not None

def test_play(spotify_user_auth, depeche_mode_artist_id):
    assert spotify_user_auth.play(depeche_mode_artist_id) is not None

def test_pause(spotify_user_auth):
    assert spotify_user_auth.pause() is not None

def test_play(spotify_user_auth):
    assert spotify_user_auth.play() is not None

def test_currently_playing(spotify_user_auth):
    assert spotify_user_auth.currently_playing()

def test_currently_playing_info(spotify_user_auth):
    assert spotify_user_auth.currently_playing_info()

def test_previous(spotify_user_auth):
    assert spotify_user_auth.previous() is not None

def test_next(spotify_user_auth):
    assert spotify_user_auth.next() is not None

def test_repeat(spotify_user_auth):
    assert spotify_user_auth.repeat() is not None

def test_shuffle(spotify_user_auth):
    assert spotify_user_auth.shuffle() is not None

def test_seek(spotify_user_auth):
    assert spotify_user_auth.seek(10000) is not None  # 10 seconds

def test_volume(spotify_user_auth):
    assert spotify_user_auth.volume(72) is not None
    assert spotify_user_auth.volume(32) is not None

def test_pause(spotify_user_auth):
    assert spotify_user_auth.pause() is not None

###### Test playlists

def test_create_playlist(spotify_user_auth, new_playlist_name):
    assert spotify_user_auth.create_playlist(new_playlist_name) is not None

def test_update_playlist(spotify_user_auth, new_playlist_id, new_playlist_name):
    assert spotify_user_auth.update_playlist(new_playlist_id, 'NEWNAMENOONECANTHINKOF') is not None
    assert spotify_user_auth.update_playlist(new_playlist_id, new_playlist_name) is not None

def test_add_playlist_tracks(spotify_user_auth, new_playlist_id, them_bones_track_id, gods_plan_track_id):
    assert spotify_user_auth.add_playlist_tracks(new_playlist_id, [them_bones_track_id, gods_plan_track_id]) is not None

def test_playlist_tracks(spotify_user_auth, new_playlist_id, them_bones_track_id):
    assert spotify_user_auth.playlist_tracks(new_playlist_id)

def test_reorder_playlist_track(spotify_user_auth, new_playlist_id, sonne_track_id):
    assert spotify_user_auth.add_playlist_tracks(new_playlist_id, sonne_track_id) is not None
    assert spotify_user_auth.reorder_playlist_track(new_playlist_id, range_start=1, insert_before=0) is not None

def test_delete_playlist_tracks(spotify_user_auth, new_playlist_id, gods_plan_track_id, them_bones_track_id):
    assert spotify_user_auth.delete_playlist_tracks(
        new_playlist_id,
        [
            {
                'uri': gods_plan_track_id,
                'positions': 0
            },
            {
                'uri': them_bones_track_id,
                'positions': 1
            }  
        ]
    ) is not None

def test_delete_playlist(spotify_user_auth, new_playlist_id):
    assert spotify_user_auth.delete_playlist(new_playlist_id) is not None

####### Test profile

def test_me(spotify_user_auth):
    assert spotify_user_auth.me

def test_user_profile(spotify_user_auth, john_smith_user_id):
    assert spotify_user_auth.user_profile(john_smith_user_id)

