<p align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/e/eb/Spotify_meaningful_logo.svg" alt="Logo" title="Spotify" height="300" width="300"/>
  <p align="center">
    <a href="https://travis-ci.org/omarryhan/pyfy"><img alt="Build Status" src="https://travis-ci.org/omarryhan/pyfy.svg?branch=master"></a>
    <a href="https://github.com/omarryhan/pyfy"><img alt="Software License" src="https://img.shields.io/badge/license-MIT-brightgreen.svg?style=flat-square"></a>
  </p>
</p>

# Web API Wrapper for Spotify in Python

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

## Documentation

[Link to Readthedocs](https://pyfy.readthedocs.io/en/latest)

## Setup

    $ pip install --upgrade --user pyfy


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

**1. Make a single call:**

    import asyncio
    from pyfy import AsyncSpotify

    spt = AsyncSpotify('your_access_token')

    async def query():
        return await spt.search('Like a motherless child')

    asyncio.run(query())

*or even:*

    awaited_search_result = asyncio.run(spt.search('A tout le monde'))

**2. Make multiple calls using a single TCP connection (no async/await syntax):**

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

**3. To manually await the results:**

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

    results = asyncio.run(runner())

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
            return redirect(spt.auth_uri())

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
    client = ClientCreds(client_id='aclientid', client_secret='averysecrettoken')

    # Load from environment
    client = ClientCreds()
    client.load_from_env()

    # Load from json file
    client = ClientCreds()
    client.load_from_json(path='full/dir/path', name='name_of_the_json_file')

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

## Contribute

- All kinds of contributions are welcome :)

## Contributors

- 