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

## Quick Start

**Sync:**

```python 3.7
from pyfy import Spotify

spt = Spotify('your_access_token')

spt.user_playlists()
spt.play()
spt.volume(85)
spt.next()
spt.pause()
results = spt.search(q='alice in chains them bones')
print(results)
```

**Async:**

```python 3.7
import asyncio
from pyfy import AsyncSpotify

spt = AsyncSpotify('your_access_token')

async def query():
    return await spt.search('Like a motherless child')

res = asyncio.run(query())

print(res)
```

## Documentation 📑

**Readthedocs:** (https://pyfy.readthedocs.io/en/latest)

## Setup ⚙️

```bash
$ pip install pyfy
```

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

## Contact 📧

I currently work as a freelance software devloper. Like my work and got a gig for me?

Want to hire me fulltime? Send me an email @ omarryhan@gmail.com

## Buy me a coffee ☕

**Bitcoin:** 3NmywNKr1Lzo8gyNXFUnzvboziACpEa31z

**Ethereum:** 0x1E1400C31Cd813685FE0f6D29E0F91c1Da4675aE

**Bitcoin Cash:** qqzn7rsav6hr3zqcp4829s48hvsvjat4zq7j42wkxd

**Litecoin:** MB5M3cE3jE4E8NwGCWoFjLvGqjDqPyyEJp

**Paypal:** https://paypal.me/omarryhan
