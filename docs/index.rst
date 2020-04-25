.. Pyfy documentation master file, created by
   sphinx-quickstart on Sun Nov 25 18:23:32 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Pyfy's documentation!
================================

Pyfy is an Async + Sync Pythonic Spotify Client that focuses on ease of use and API stability.

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


Authentication👩‍🎤
=====================

Choose one of:

**1. Authorization Code Flow (OAuth2) (recommended)** `examples with Sanic(async) and Flask(sync) <https://github.com/omarryhan/Pyfy/tree/master/examples>`_

.. code-block:: python3

    from pyfy import Spotify, ClientCreds, UserCreds, AuthError, ApiError

    client = ClientCreds(client_id='clientid', client_secret='client_secret')
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

Same as OAuth2 but without a refresh token. Suitable for quick runs.

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

Spotify API Reference 🎶
==========================

Visit: https://developer.spotify.com/documentation/web-api/reference/

Sync Client 🎸
================

.. autoclass:: pyfy.sync_client.Spotify
    :members:
    :undoc-members:
    :show-inheritance:
    :inherited-members:

Async Client 🎼
=================

.. autoclass:: pyfy.async_client.AsyncSpotify
    :members:
    :undoc-members:
    :show-inheritance:
    :inherited-members:

Exceptions ⚠️
==============

.. automodule:: pyfy.excs
    :members:
    :undoc-members:
    :show-inheritance:
    :inherited-members:

Credentials 📇
===============

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

