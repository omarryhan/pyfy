[![Build Status](https://travis-ci.org/omarryhan/Pyfy.svg?branch=master)](https://travis-ci.org/omarryhan/Pyfy)
# Spotify Web API Wrapper
## ** UNDER DEVELOPMENT **
<img src="https://newsroom.spotify.com/media/mediakit/2018-03-19_22-28-43/Spotify_Logo_CMYK_Green.png" alt="picture" style="width:300px;"/>


## Features

- Supports:
  - OAuth2 client credentials flow
  - OAuth2 authroization code flow
  - Access token only authentication
- Automatically refreshes tokens for client and users
- Descriptive errors
- Unit and integration tested
- Fit for both production and experimental/personal environments
- Able to automatically default to user's local country

## Quick Start

### 1. By Client Credentials:  *[get from here](https://developer.spotify.com/dashboard/applications)

    from pyfy import ClientCredentials, Client

    client_creds = ClientCredentials(client_id=<client_id>, client_secred=<client_secret>_)
    client = Client(client_creds)
    client.authorize_client_creds()
    json_search_results = client.search(q='alice in chains them bones')

### 2. By User's Access Token: *[get from here](https://beta.developer.spotify.com/console/get-current-user/)

    from pyfy import Client, UserCredentials

    user_creds = UserCredentials(access_token='user\'s access token')
    client = Client(user_creds=user_creds)
    client.playback_play()
    client.playback_pause()

### 3. With Authorization code flow (OAuth2)

    from pyfy import Client, ClientCredentials, UserCredentials, AuthError, ApiError

    client_creds = ClientCredentials(client_id='clientid', client_secret='client_secret')
    client = Client(client_creds)
    
    def authorize():
        # Fist step of OAuth, Redirect user to spotify's authorization endpoint
        if client.is_oauth_ready:
            return redirect(client.oauth_uri)

    # Authorization callback
    def callback(grant):
        try:
            user_creds = client.build_credentials(grant=grant, set_user=True)
        except AuthError as e:
            abort(401)
            logging.info(e.msg)
            logging.info(e.http_response)
        else:
            db.insert(user_creds)

    def get_user_tracks():
        try:
            return json.dumps(client.get_user_tracks())
        except ApiError:
            abort(500)

### 👨. Ways to load Credentials (User & Client)
    # Instantiate directly
    client_creds = ClientCredentials(client_id='aclientid', client_secret='averysecrettok**')

    # Load from environment
    client_creds = ClientCredentials()
    client_creds.load_from_env()

    # Load from json file
    client_creds = ClientCredentials()
    client_creds.load_from_json(path=<full/file/path>, name=<file\'s_name>)

### 🎝🎶 Resources 🎶🎝

    # User owned resources
    client.get_tracks():
        pass


## Setup

    $ pip install pyfy

## Testing

### Unit test:

    $ tox

### Inttegration test:

1. Copy the `spt_keys_template.py` to a new file and call it `spt_keys.py` as this file will be automatically gitignored.
2. Now you can safely save your keys there for testing purposes. Here's an example:
    1. `SPOTIFY_CLIENT_ID` Create an app from [here](https://developer.spotify.com/dashboard/applications)
    2. `SPOTIFY_CLIENT_SECRET` Create an app from [here](https://developer.spotify.com/dashboard/applications)
    3. `SPOTIFY_ACCESS_TOKEN` Get a Spotify token from [here](https://beta.developer.spotify.com/console/get-current-user/)  ****Check all scopes**
    4. `SPOTIFY_REDIRECT_URI` = 'http://localhost:5000/callback/spotify',  # You have to register this call back in your Application's dashboard https://developer.spotify.com/dashboard/applications
    5. `PYFY_TEST_INTEGRATION` = true
3. Run:

    *this will run some tests using your client ID, client secret, access token and user ID<br>
    *Unfortunately Spotify does not have a sandbox API, so we have to test it against the live API<br>
    *The tests will carefully teardown all resources created<br>
    *Integration tests will not be abusive to the API and should only test for successfull integration with minimum API calls<br>
    *OAuth2 flow isn't tested in the tests folder. Instead you can test it manually from the examples folder by: `pip install flask pyfy && python examples/oauth.py`<br>

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

- ClientCredentials

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

- UserCredentials

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

- Client

  - client_creds
  - user_creds
  - authorize_client_creds()
  - oauth_uri
  - is_oauth_ready
  - is_active
  - build_user_credentials()

  - Resources....
