<p align="center">
  <img src="https://upload.wikimedia.org/wikipedia/commons/e/eb/Spotify_meaningful_logo.svg" alt="Logo" title="Spotify" height="300" width="300"/>
  <p align="center">
    <a href="https://travis-ci.org/omarryhan/pyfy"><img alt="Build Status" src="https://travis-ci.org/omarryhan/pyfy.svg?branch=master"></a>
    <a href="https://github.com/omarryhan/pyfy"><img alt="Software License" src="https://img.shields.io/badge/license-MIT-brightgreen.svg?style=flat-square"></a>
    <a href="https://github.com/python/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg" /></a>
    <a href="https://pepy.tech/badge/pyfy"><img alt="Downloads" src="https://pepy.tech/badge/pyfy"></a>
    <a href="https://pepy.tech/badge/pyfy/month"><img alt="Monthly Downloads" src="https://pepy.tech/badge/pyfy/month"></a>
  </p>
</p>

# Pyfy

Pyfy is an Async + Sync Pythonic Spotify Client that focuses on ease of use and API stability.

## Setup ⚙️

```bash
$ pip install pyfy
```

## Quick Start

**Sync:**

```python 3.7
from pyfy import Spotify

spt = Spotify('your_access_token')

spt.play()
spt.volume(85)
spt.next()
spt.pause()
```

**Async:**

```python 3.7
import asyncio
from pyfy import AsyncSpotify

spt = AsyncSpotify('your_access_token')

async def search():
    return await spt.search('A tout le monde')

search_result = asyncio.run(search())
```

## Authentication 👩‍🎤

Choose one of:

**1. Authorization Code Flow (OAuth2)** (recommended) [examples with Sanic(async) and Flask(sync)](https://github.com/omarryhan/Pyfy/tree/master/examples)

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

**2. User's Access Token:**  [get from here](https://beta.developer.spotify.com/console/get-current-user/)

Same as OAuth2 but without a refresh token. Suitable for quick runs.

.. code-block:: python3

    from pyfy import Spotify

    spt = Spotify('your access token')

**3. Client Credentials Flow (OAauth2):**  [get from here](https://developer.spotify.com/dashboard/applications)

Suitable for when you want to access public information quickly. (Accessing user information is porhibited using this method)

.. code-block:: python3

    from pyfy import ClientCreds, Spotify

    client = ClientCreds(client_id=client_id, client_secret=client_secret)
    spt = Spotify(client_creds=client)
    spt.authorize_client_creds()

## API

**Sync:** https://pyfy.readthedocs.io/en/latest/#sync-client
**Async:** https://pyfy.readthedocs.io/en/latest/#async-client

**Spotify's:** https://developer.spotify.com/documentation/web-api/reference/

## Documentation 📑

**Readthedocs:** https://pyfy.readthedocs.io/en/latest


## Backward Incompatibility Notices

**V2:**

1. Removed `Spotify.oauth_uri` property in favor of `Spotify.auth_uri` method.

2. `Spotify.play()` now accepts, `track_ids`, `artist_ids` etc. instead of `resource_ids` + `resource_names`

3. Oauth2 state handling:

   - Removed deprecated `enforce_state_check` functionality

   - Removed state attribute from `user_creds`

   - Oauth2 state checking is no longer done by Pyfy's client and should be handled manually

## Contributors

Big thank you to our amazing contributors:

- [exofeel](https://github.com/exofeel)
- [Schiism](https://github.com/Schiism)
- [kevinhynes](https://github.com/kevinhynes)
- [haykkh](https://github.com/haykkh)
- [ykelle](https://github.com/ykelle)
- [Patrick Arminio](https://github.com/patrick91)
- [Mustafa](https://github.com/ms7m)


## Contact 📧

I currently work as a freelance software devloper. Like my work and got a gig for me?

Want to hire me fulltime? Send me an email @ omarryhan@gmail.com

## Buy me a coffee ☕

**Bitcoin:** 3NmywNKr1Lzo8gyNXFUnzvboziACpEa31z

**Ethereum:** 0x1E1400C31Cd813685FE0f6D29E0F91c1Da4675aE

**Bitcoin Cash:** qqzn7rsav6hr3zqcp4829s48hvsvjat4zq7j42wkxd

**Litecoin:** MB5M3cE3jE4E8NwGCWoFjLvGqjDqPyyEJp

**Paypal:** https://paypal.me/omarryhan
