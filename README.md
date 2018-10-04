<p align="center">
  <img src="https://newsroom.spotify.com/media/mediakit/2018-03-19_22-28-43/Spotify_Logo_CMYK_Green.png" alt="Logo" style="width:700px;"/>
  <p align="center">
    <a href="https://travis-ci.org/omarryhan/Pyfy"><img alt="Build Status" src="https://travis-ci.org/omarryhan/Pyfy.svg?branch=master"></a>
    <a href="https://github.com/omarryhan/Pyfy"><img alt="Software License" src="https://img.shields.io/badge/license-MIT-brightgreen.svg?style=flat-square"></a>
  </p>
</p>

# Spotify's Web API Wrapper


## Features

- Support for:
  - OAuth2 client credentials flow
  - OAuth2 authroization code flow
  - Access token only authorization
- Automatically refreshes tokens for client and users
- Descriptive errors
- Unit and integration tested
- Fit for both production and experimental/personal environments
- Able to automatically default to user's locales
- Neatly handles type conversions when necessary
- Support for HTTP caching

## Quick Start

    from pyfy import Spotify

    spt = Spotify('your_access_token')

    spt.user_playlists()
    spt.play()
    spt.volume(85)
    spt.next()
    spt.pause()
    json_search_results = spt.search(q='alice in chains them bones')

## Authentication and Authorization

### 1. By User's Access Token: *[get from here](https://beta.developer.spotify.com/console/get-current-user/)

    from pyfy import Spotify

    spt = Spotify('your access token')

### 2. With Client Credentials Flow (OAauth2):  *[get from here](https://developer.spotify.com/dashboard/applications)

    from pyfy import ClientCreds, Spotify

    client = ClientCreds(client_id=client_id, client_secret=client_secret)
    spt = Spotify(client_creds=client)
    spt.authorize_client_creds()

### 3. With Authorization Code Flow (OAuth2) *[example here](https://github.com/omarryhan/Pyfy/tree/master/examples)

    from pyfy import Spotify, ClientCreds, UserCreds, AuthError, ApiError

    client = ClientCreds(client_id='clientid', client_secret='client_secret')
    spt = Spotify(client)

    def authorize():
        # Fist step of OAuth, Redirect user to spotify's authorization endpoint
        if spt.is_oauth_ready:
            return redirect(spt.oauth_uri)

    # Authorization callback
    def callback(grant):
        try:
            user_creds = spt.build_credentials(grant=grant)
        except AuthError as e:
            abort(401)
            logging.info(e.msg)
            logging.info(e.http_response)
        else:
            db.insert(user_creds)
            return redirect(url_for_home)

    def get_user_tracks():
        try:
            return json.dumps(spt.user_tracks())
        except ApiError:
            abort(500)

### 👨 Ways to load Credentials (User & Client)
    # Instantiate directly
    client = ClientCreds(client_id='aclientid', client_secret='averysecrettok**')

    # Load from environment
    client = ClientCreds()
    client.load_from_env()

    # Load from json file
    client = ClientCreds()
    client.load_from_json(path=<full/file/path>, name=files_name)

## 🎶 Resources

- Playback:
  - devices()
  - play()
  - pause()
  - repeat()
  - seek()
  - previous()
  - shuffle()
  - recently_played_tracks()
  - currently_playing_info()
  - currently_playing()
  - playback_transfer()
  - volume()
- Playlists:
  - playlist()
  - user_playlists()
  - follows_playlist()
  - follow_playlist()
  - create_playlist()
  - update_playlist()
  - unfollow_playlist()
  - delete_playlist()
- Playlist Contents:
  - playlist_tracks():
  - add_playlist_tracks()
  - reorder_playlist_track()
  - delete_playlist_tracks()
- Tracks:
  - tracks()
  - user_tracks()
  - owns_tracks()
  - save_tracks()
  - delete_tracks()
  - user_top_tracks()
- Albums:
  - albums()
  - user_albums()
  - owns_albums()
  - save_albums()
  - delete_albums()
- Artists:
  - artists()
  - followed_artists()
  - follows_artists()
  - follow_artists()
  - artist_related_artists()
- Users:
  - me
  - is_premium
  - user_profile()
  - follows_users()
  - unfollow_users()
  - follow_users()       
- Others:
  - user_top_artists()
  - artist_albums()
  - album_tracks()
  - artist_top_tracks()
  - next_page()
  - previous_page()
- Explore and Personalization:
  - available_genre_seeds()
  - categories()
  - category_playlist()
  - featured_playlists()
  - new_releases()
  - search()
  - recommendations()
  - tracks_audio_features()

## Installation and Setup

    $ pip install -U pyfy

## Testing

### Unit tests:

    $ tox

### Integration tests:

1. Copy the `spt_keys_template.py` to a new file and call it `spt_keys.py` as this file will be automatically gitignored.
2. Now you can safely save your keys there for testing purposes. Here's an example:
    1. `SPOTIFY_CLIENT_ID` Create an app from [here](https://developer.spotify.com/dashboard/applications)
    2. `SPOTIFY_CLIENT_SECRET` Create an app from [here](https://developer.spotify.com/dashboard/applications)
    3. `SPOTIFY_ACCESS_TOKEN` Get a Spotify token from [here](https://beta.developer.spotify.com/console/get-current-user/)  ****Check all scopes**
    4. `SPOTIFY_REDIRECT_URI` = 'http://localhost:5000/callback/spotify',  # You have to register this call back in your Application's dashboard https://developer.spotify.com/dashboard/applications
    5. `PYFY_TEST_INTEGRATION` = true
3. Run:

    *This will run some tests using your client ID, client secret and access token.<br>
    *Unfortunately Spotify does not have a sandbox API, so we have to test it against the live API<br>
    *The tests will carefully teardown all resources created<br>
    *Integration tests will not be abusive to the API and should only test for successful integration with minimum API calls<br>
    *OAuth2 flow isn't tested in the tests folder. Instead you can test it manually from the examples folder by running: `pip install flask pyfy && python examples/oauth2.py`<br>
    *Use [the documentation](https://developer.spotify.com/documentation/web-api/reference/) instead of the [console](https://developer.spotify.com/console/get-album/?id=0sNOF9WDwhWunNAHPD3Baj) for reading the docs, as some console endpoints aren't up to date with the documentation. Namely: 1. Create User Playlist 2. Recommendations<br>

        $ tox

## API

### Errors

- SpotifyError 

- ApiError(SpotifyError)
  
  - msg
  - http_response
  - http_request
  - code 

- AuthError(SpotifyError)
  
  - msg
  - http_response
  - http_request
  - code

### Creds

- ClientCreds

  - pickle()
  - save_as_json()
  - load_from_json()
  - load_from_env()
  - access_is_expired

  - client_id
  - client_secret
  - redirect_uri
  - scopes
  - show_dialog
  - access_token
  - expiry

- UserCreds

  - pickle()
  - save_as_json()
  - load_from_json()
  - load_from_env()
  - access_is_expired

  - access_token
  - refresh_token
  - expiry
  - user_id
  - state

- Spotify

  - client_creds
  - user_creds
  - authorize_client_creds()
  - oauth_uri
  - is_oauth_ready
  - is_active
  - is_premium
  - build_user_creds()

  - Resources....

## Contribute

- Would be nice if someone can write some documentations. Maybe using Sphynx?
- More unit and integration tests
