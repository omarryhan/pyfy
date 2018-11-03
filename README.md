<p align="center">
  <img src="https://newsroom.spotify.com/media/mediakit/2018-03-19_22-28-43/Spotify_Logo_CMYK_Green.png" alt="Logo" style="width:700px;"/>
  <p align="center">
    <a href="https://travis-ci.org/omarryhan/Pyfy"><img alt="Build Status" src="https://travis-ci.org/omarryhan/Pyfy.svg?branch=master"></a>
    <a href="https://github.com/omarryhan/Pyfy"><img alt="Software License" src="https://img.shields.io/badge/license-MIT-brightgreen.svg?style=flat-square"></a>
  </p>
</p>

# Spotify's Web API Wrapper


## Features

- Async and Sync clients
- Authenticate using:
  - OAuth2 client credentials flow
  - OAuth2 authroization code flow
  - Access token only authorization
- Covers every parameter for every endpoint in Spotify's Web API
- Automatically refreshes tokens for clients and users
- Descriptive errors
- Able to automatically default to user's locales
- Rate limiting
- HTTP and SOCKS proxies
- HTTP caching (Sync only)
- Unit and integration tested
- Fit for both production and experimental/personal environments
- Begginner friendly interface
- Almost identical Async and Sync Interfaces

## Quick Start

### Sync

    from pyfy import Spotify

    spt = Spotify('your_access_token')

    spt.user_playlists()
    spt.play()
    spt.volume(85)
    spt.next()
    spt.pause()
    results = spt.search(q='alice in chains them bones')
    print(results)

### Async

**Make a single call:**

    import asyncio
    from pyfy import AsyncSpotify

    spt = AsyncSpotify('your_access_token')

    async def query():
        return await spt.search('Like a motherless child')

    asyncio.run(query())

*or even:*

    awaited_search_result = asyncio.run(spt.search('A tout le monde'))

**Make multiple calls using a single TCP connection (no async/await syntax):**
    from pprint import pprint
    from pyfy import AsyncSpotify

    spt = AsyncSpotify('your_access_token')

    gathered_results = spt.gather_now(
        spt.search('Seize the day', to_gather=True),
        spt.search('Feel good inc'', to_gather=True),
        spt.search('In your room', to_gather=True),
        spt.search('Tout Petit Moineau', to_gather=True)
    )

    pprint(gathered_results)

**If you have an event loop already running:**

    import asyncio
    from pyfy import AsyncSpotify

    spt = AsyncSpotify('your_access_token')

    async def runner():
        return await spt.gather(
            spt.search('Saeed', to_gather=True),
            spt.search('Killing time', to_gather=True),
            spt.search('Project 100', to_gather=True),
            spt.search('Tout Petit Moineau', to_gather=True)
        )

    asyncio.run(runner())

## Authentication and Authorization

### 1. With User's Access Token:  *[get from here](https://beta.developer.spotify.com/console/get-current-user/)

    from pyfy import Spotify

    spt = Spotify('your access token')

### 2. With Client Credentials Flow (OAauth2):  *[get from here](https://developer.spotify.com/dashboard/applications)

    from pyfy import ClientCreds, Spotify

    client = ClientCreds(client_id=client_id, client_secret=client_secret)
    spt = Spotify(client_creds=client)
    spt.authorize_client_creds()

### 3. With Authorization Code Flow (OAuth2) *[examples with Sanic(async) and Flask(sync) here](https://github.com/omarryhan/Pyfy/tree/master/examples)

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
  - me()
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

    $ pip install --upgrade --user pyfy

**For Python3.7:**

    $ python3.7 -m pip install --upgrade --user pyfy

**Optional for Async:**

- Faster encoding detector lib written in C:

      $ pip install --user cchardet  

- Async DNS requests:

      $ pip install --user aiodns

- Faster JSON parser written in C:
  
      $ pip install --user ujson

## Testing

### Unit tests:

    $ tox

### Integration tests:

1. Copy the `spt_keys_template.py` to a new file and call it `spt_keys.py` as this file will be automatically gitignored.
2. Now you can safely save your keys there for testing purposes. Here's an example:
    1. `SPOTIFY_CLIENT_ID` Create an app from [here](https://developer.spotify.com/dashboard/applications)
    2. `SPOTIFY_CLIENT_SECRET` Create an app from [here](https://developer.spotify.com/dashboard/applications)
    3. `SPOTIFY_ACCESS_TOKEN` Get a Spotify token from [here](https://developer.spotify.com/console/get-current-user/)  ****Check all scopes**
    4. `SPOTIFY_REFRESH_TOKEN` To avoid manually refreshing your access token from the dev console, run the Oauth2 example in the examples dir. Then copy and paste the refresh token returned here. 
    5. `SPOTIFY_REDIRECT_URI` = 'http://localhost:5000/callback/spotify',  # You have to register this callback in your Application's dashboard https://developer.spotify.com/dashboard/applications
    6. `PYFY_TEST_INTEGRATION_SYNC` = 'true'
    7. `PYFY_TEST_INTEGRATION_ASYNC` = 'true'
3. Run:

    *This will run some tests using your client ID, client secret and access token.<br>
    *Unfortunately Spotify does not have a sandbox API, so we have to test it against the live API<br>
    *Tests will carefully teardown all resources created and/or modified<br>
    *Integration tests will not be abusive to the API and should only test for successful integration with minimum API calls<br>
    *OAuth2 flow isn't tested in the tests folder (yet). Instead you can manually test it in the examples folder by running: `pip install flask pyfy && python examples/oauth2.py`<br>

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
  - unpickle()  # Class method
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
  - unpickle()  # Class method
  - save_as_json()
  - load_from_json()
  - load_from_env()
  - access_is_expired

  - access_token
  - refresh_token
  - expiry
  - user_id
  - state

### Clients

- Spotify

  - client_creds
  - user_creds
  - authorize_client_creds()
  - oauth_uri
  - is_oauth_ready
  - is_active
  - is_premium
  - build_user_creds()
  - populate_user_creds()

  - *resources*.... 

- AsyncSpotify

  - client_creds
  - user_creds
  - coro: authorize_client_creds()
  - oauth_uri
  - is_oauth_ready
  - coro: is_active
  - coro: is_premium
  - coro: build_user_creds()
  - coro: populate_user_creds()

  - *resources*....

## Please Note:

- Use the [documentation](https://developer.spotify.com/documentation/web-api/reference/) instead of the [console](https://developer.spotify.com/console/get-album/?id=0sNOF9WDwhWunNAHPD3Baj) for reading the docs, as some console endpoints aren't up to date with the documentation. Namely: 1. Create User Playlist 2. Recommendations<br>

## Contribute

- Would be nice if someone can write some documentations. Maybe using Sphinx?
- More unit and integration tests

## Contributors

- 