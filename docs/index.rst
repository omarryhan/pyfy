.. Pyfy documentation master file, created by
   sphinx-quickstart on Sun Nov 25 18:23:32 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Pyfy's documentation! 👋
======================================

Pyfy is a Sync + Async Pythonic Spotify Client that focuses on ease of use in personal projects and API stability and security for production grade codebases.

Setup 🥁
=========

.. code-block:: bash

    $ pip install pyfy

Quick Start 🎛️
===============

**Sync**

.. code-block:: python3

    from pyfy import Spotify

    spt = Spotify('your_access_token')

    spt.play()
    spt.volume(85)
    spt.next()
    spt.pause()

**Async**

.. code-block:: python3

    import asyncio
    from pyfy import AsyncSpotify

    spt = AsyncSpotify('your_access_token')

    async def search():
        return await spt.search('A tout le monde')

    search_result = asyncio.run(search())


Getting Started 👩
========================

You should start by creating client credentials from Spotify's `Developer's console <https://developer.spotify.com/dashboard/applications>`_.

Next, edit your application's settings and set a Redirect URL. If it's for personal use then set it as:

  http://localhost:9000 *Port can be any port of choice, not necessarily 9000*

Next, copy your:

1. Client ID
2. Client Secret
3. Redirect URL (That you just set)

Next, figure out the scopes that you think you'll need from here: https://developer.spotify.com/documentation/general/guides/scopes/

e.g. ``["user-library-modify", "app-remote-control"]``

Next, follow the first authentication scheme from below (it's the one you'll most likely need, unless you're sure otherwise)

Authentication 👩‍🎤
=====================

Suitable if you want to access user-related resources. e.g. user-playlists, user-tracks etc.

`Click here for full working examples with Sanic(async) and Flask(sync) <https://github.com/omarryhan/Pyfy/tree/master/examples>`_.

**1. Authorization Code Flow (OAuth2) (recommended)**

.. code-block:: python3

    from pyfy import Spotify, ClientCreds, UserCreds, AuthError, ApiError

    client = ClientCreds(
        client_id='clientid',
        client_secret='client_secret',
        redirect_uri='https://localhost:9000",
        scopes=["user-library-modify", "app-remote-control"]
    )
    spt = Spotify(client_creds=client)

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

**2. User's Access Token:** `get from here <https://beta.developer.spotify.com/console/get-current-user/>`_

Same as the Authorization Code Flow above but without a refresh token. Suitable for quick runs.

.. code-block:: python3

    from pyfy import Spotify

    spt = Spotify('your access token')

**3. Client Credentials Flow (OAuth2):**  `get from here <https://developer.spotify.com/dashboard/applications>`_

Suitable for when you want to access public information quickly. (Accessing user information is porhibited using this method)

.. code-block:: python3

    from pyfy import ClientCreds, Spotify

    client = ClientCreds(client_id=client_id, client_secret=client_secret)
    spt = Spotify(client_creds=client)
    spt.authorize_client_creds()

API endpoints 🌐
===================

Albums
-----------

- **Get an album:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.albums
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/albums/get-album/

- **Get an album's tracks:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.album_tracks
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/albums/get-albums-tracks/

- **Get several albums:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.albums
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/albums/get-several-albums/

Artists
-------------

- **Get an artist:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.artists
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/artists/get-artist/

- **Artist albums:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.artist_albums
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/artists/get-artists-albums/

- **Artist top tracks:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.artist_top_tracks
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/artists/get-artists-top-tracks/

- **Artist related artists:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.artist_related_artists
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/artists/get-related-artists/

- **Get several artists:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.artists
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/artists/get-several-artists/

Browse
-----------

- **Get a category:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.category
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/browse/get-category/

- **Get a category's playlists:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.category_playlist
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/browse/get-categorys-playlists/

- **Get list of categories:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.categories
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/browse/get-list-categories/

- **Get a list of featured playlists:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.featured_playlists
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/browse/get-list-featured-playlists/

- **Get a list of new releases:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.new_releases
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/browse/get-list-new-releases/

- **Get recommendations based on seeds:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.recommendations
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/browse/get-recommendations/

Episodes
-----------

- **Get an episode:**

  - Pyfy: **TODO**
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/episodes/get-an-episode/

- **Get several episodes:**

  - Pyfy: **TODO**
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/episodes/get-several-episodes/ 

Follow
------------

- **Check if Current User Follows Artists or Users:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.follows_users
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/follow/check-current-user-follows/

- **Check if Users Follow a Playlist:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.follows_playlist
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/follow/check-user-following-playlist/

- **Follow Artists:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.follow_artists
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/follow/follow-artists-users/

- **Follow Users:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.follow_artists
  - Web API reference: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.follow_users

- **Follow a playlist:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.follow_playlist
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/follow/follow-playlist/

- **Get User's Followed Artists:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.followed_artists
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/follow/get-followed/

- **Unfollow Artists:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.unfollow_artists
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/follow/unfollow-artists-users/

- **Unfollow Users:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.unfollow_users
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/follow/unfollow-artists-users/

- **Unfollow Playlist:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.unfollow_playlist
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/follow/unfollow-playlist/

User Library
----------------

- **Check User's Saved Albums:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.owns_albums
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/library/check-users-saved-albums/

- **Check User's Saved Shows:**

  - Pyfy: **TODO**
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/library/check-users-saved-shows/

- **Check User's Saved Tracks:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.owns_tracks
  - Web API reference: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.owns_tracks

- **Get Current User's Saved Albums:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.user_albums
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/library/get-users-saved-albums/

- **Get User's Saved Shows:**

  - Pyfy: **TODO**
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/library/get-users-saved-shows/

- **Get a User's Saved Tracks:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.user_tracks
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/library/get-users-saved-tracks/

- **Remove Albums for Current User:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.delete_albums
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/library/remove-albums-user/

- **Remove User's Saved Shows:**

  - Pyfy: **TODO**
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/library/remove-shows-user/

- **Remove User's Saved Tracks:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.delete_tracks
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/library/remove-tracks-user/

- **Save Albums for Current User:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.save_albums
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/library/save-albums-user/

- **Save Shows for Current User:**

  - Pyfy: **TODO**
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/library/save-shows-user/

- **Save Tracks for User:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.save_tracks
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/library/save-tracks-user/

Personalization
--------------------

- **Get a User's Top Artists:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.user_top_artists
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/personalization/get-users-top-artists-and-tracks/

- **Get a User's Top Tracks:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.artist_top_tracks
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/personalization/get-users-top-artists-and-tracks/

Player
-------------

- **Add an Item to the User's Playback Queue:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.queue
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/player/add-to-queue/

- **Get a User's Available Devices:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.devices
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/player/get-a-users-available-devices/

- **Get Information About The User's Current Playback:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.currently_playing_info
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/player/get-information-about-the-users-current-playback/

- **Get Current User's Recently Played Tracks:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.recently_played_tracks
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/player/get-recently-played/

- **Get the User's Currently Playing Track:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.currently_playing
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/player/get-the-users-currently-playing-track/

- **Pause a User's Playback:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.pause
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/player/pause-a-users-playback/

- **Seek To Position In Currently Playing Track:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.seek
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/player/seek-to-position-in-currently-playing-track/

- **Set Repeat Mode On User’s Playback:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.repeat
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/player/set-repeat-mode-on-users-playback/

- **Set Volume For User's Playback:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.volume
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/player/set-volume-for-users-playback/

- **Skip User’s Playback To Next Track:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.next
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/player/skip-users-playback-to-next-track/

- **Skip User’s Playback To Previous Track:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.previous
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/player/skip-users-playback-to-previous-track/

- **Start/Resume a User's Playback:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.play
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/player/start-a-users-playback/

- **Toggle Shuffle For User’s Playback:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.shuffle
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/player/toggle-shuffle-for-users-playback/

- **Transfer a User's Playback:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.playback_transfer
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/player/transfer-a-users-playback/

Playlists
------------

- **Add playlist items:**

  - Docs: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.add_playlist_tracks
  - Web API Reference: https://developer.spotify.com/documentation/web-api/reference/playlists/add-tracks-to-playlist/

- **Edit playlist:**

  - Pyfy: https://developer.spotify.com/documentation/web-api/reference/playlists/change-playlist-details/
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/playlists/change-playlist-details/

- **Create playlist:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.create_playlist
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/playlists/create-playlist/

- **List a user's playlists:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.user_playlists
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/playlists/get-a-list-of-current-users-playlists/

- **Playlist cover:**

  - Pyfy: **TODO**
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/playlists/get-playlist-cover/

- **List a playlist:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.playlist
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/playlists/get-playlist/

- **List a playlist items:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.playlist_tracks
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/playlists/get-playlists-tracks/

- **Remove playlist items:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.delete_playlist_tracks
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/playlists/remove-tracks-playlist/

- **Reorder playlist items:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.reorder_playlist_track
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/playlists/reorder-playlists-tracks/

- **Replace playlist items:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.replace_playlist_tracks
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/playlists/replace-playlists-tracks/

- **Upload custom playlist cover image:**

  - Pyfy: **TODO**
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/playlists/upload-custom-playlist-cover/

- **List current user playlists:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.user_playlists
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/playlists/get-a-list-of-current-users-playlists/

Search
-----------

- **Search for an item:**

  - Pyfy: https://developer.spotify.com/documentation/web-api/reference/search/search/
  - Web API reference: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.search

Shows
-----------

- **Get a Show:**

  - Pyfy: **TODO**
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/shows/get-a-show/

- **Get Several Shows:**

  - Pyfy: **TODO**
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/shows/get-several-shows/

- **Get a Show's Episodes:**

  - Pyfy: **TODO**
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/shows/get-shows-episodes/

Tracks
-------------

- **Get Audio Analysis for a Track:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.track_audio_analysis
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/tracks/get-audio-analysis/

- **Get Audio Features for a Track:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.tracks_audio_features
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/tracks/get-audio-features/

- **Get Audio Features for Several Tracks:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.tracks_audio_features
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/tracks/get-several-audio-features/

- **Get Several Tracks:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.tracks
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/tracks/get-several-tracks/

- **Get a Track:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.tracks
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/tracks/get-track/

Users Profile
---------------

- **Get Current User's Profile:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.user_profile
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/users-profile/get-current-users-profile/

- **Get a User's Profile:**

  - Pyfy: https://pyfy.readthedocs.io/en/latest/#pyfy.sync_client.Spotify.user_profile
  - Web API reference: https://developer.spotify.com/documentation/web-api/reference/users-profile/get-users-profile/

Pagination 📖
==================

.. code-block:: python3

  from pyfy import Spotify

  user_creds = {'access_token': '...', 'refresh_token': '....'}

  spt = Spotify(user_creds=user_creds)

  user_top_tracks = spt.user_top_tracks(limit=5)

  next_page_1 = spt.next_page(user_top_tracks)
  next_page_2 = spt.next_page(next_page_1)

  previous_page_1 = spt.previous_page(next_page_2)
  previous_page_1 === next_page_1  # True

Sync Client API 🎸
=====================

.. autoclass:: pyfy.sync_client.Spotify
    :members:
    :undoc-members:
    :show-inheritance:
    :inherited-members:

Async Client API 🎼
======================

.. autoclass:: pyfy.sync_client.Spotify
    :members:
    :undoc-members:
    :show-inheritance:
    :inherited-members:

Exceptions API ⚠️
===================

.. automodule:: pyfy.excs
    :members:
    :undoc-members:
    :show-inheritance:
    :inherited-members:

Credentials API 📇
=====================

.. automodule:: pyfy.creds
    :members:
    :undoc-members:
    :show-inheritance:
    :inherited-members:

Testing 👩‍🔬
==============

Unit tests
-------------

.. code-block:: bash

    $ tox

Integration tests
-------------------

1. Open tox.ini and change thoee values to:
    
    1. ``SPOTIFY_CLIENT_ID`` `Create an app <https://developer.spotify.com/dashboard/applications>`_
    
    2. ``SPOTIFY_CLIENT_SECRET`` `Create an app <https://developer.spotify.com/dashboard/applications>`_
    
    3. ``SPOTIFY_ACCESS_TOKEN`` `Get one <https://developer.spotify.com/console/get-current-user/>`_ or perform OAuth2 Auth Code Flow.

        .. note::

            Check all scopes when getting an access token.
    
    4. ``SPOTIFY_REFRESH_TOKEN``
    
        .. note::
        
            To avoid manually refreshing your access token from the dev console, run the Oauth2 example in the examples dir. Then copy and paste the refresh token returned to your tox file. 
    
    5. ``SPOTIFY_REDIRECT_URI = 'http://localhost:5000/callback/spotify'``
    
        .. note:: 
        
            You have to register this callback in your Application's dashboard https://developer.spotify.com/dashboard/applications
    
    6. ``PYFY_TEST_INTEGRATION_SYNC` = true``
    
    7. ``PYFY_TEST_INTEGRATION_ASYNC = true``

2. Run:

    .. note::

        * This will run some tests using your client ID, client secret and access token.
        
        * Unfortunately Spotify does not have a sandbox API, so we have to test it against the live API
        
        * Tests will carefully teardown all resources created and/or modified
        
        * Integration tests will not be abusive to the API and should only test for successful integration with minimum API calls
        
        * OAuth2 flow isn't tested in the tests folder (yet). Instead you can manually test it in the examples folder by running: ``pip install flask pyfy && python examples/oauth2.py``

    .. code-block:: bash

        $ tox


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

