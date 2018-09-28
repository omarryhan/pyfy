import os
import sys
import json
import datetime
import logging
import secrets
from urllib import parse

from requests import Request, Session

__name__ = 'pyfy'
__about__ = "Lightweight python wrapper for Spotify's web API"
__url__ = 'https://github.com/omarryhan/spyfy'
__version_info__ = ('0', '0', '1')
__version__ = '.'.join(__version_info__)
__author__ = 'Omar Ryhan'
__author_email__ = 'omarryhan@gmail.com'
__maintainer__ = 'Omar Ryhan'
__license__ = 'MIT'
__copyright__ = '(c) 2018 by Omar Ryhan'
__all__ = [
]

BASE_URI = 'https://api.spotify.com/v1/'
OAUTH_TOKEN_URL = 'https://accounts.spotify.com/api/token'
OAUTH_AUTHORIZE_URL = 'https://accounts.spotify.com/authorize'
ALL_SCOPES = []

logger = logging.getLogger(__name__)


# TODO: Set session params upon authenticating
# TODO: Implement cache https://developer.spotify.com/documentation/web-api/#conditional-requests

class SpotifyError(Exception):
    pass


class ApiError(SpotifyError):
    def __init__(self, msg, http_response=None, e=None):
        self.http_response = http_response
        self.code = http_response.status_code
        self.msg = msg
        self.original_exception = e
        if e:
            super_msg = msg + f'\nOriginal exception: {e}'
        else:
            super_msg = msg
        super(ApiError, self).__init__(super_msg)


class AuthError(SpotifyError):
    def __init__(self, http_response):
        self.http_response = http_response
        super(AuthError, self).__init__(http_response.json())


class _Creds:
    def __init__(self, *args, **kwargs):
        raise TypeError('_Creds class isn\'nt calleable')

    def load_from_file(self, path):
        pass

    def save_to_file(self, path):
        pass

    def _create_secret(self, bytes_length=32):
        return secrets.base64.standard_b64encode(secrets.token_bytes(bytes_length)).decode('utf-8')


class ClientCredentials(_Creds):
    def __init__(self, client_id=None, client_secret=None, scopes=[], redirect_uri='http://localhost', state=None, show_dialog=False):
        self.client_id = client_id
        self.client_secret = client_secret
        if not isinstance(scopes, list):
            raise TypeError('Scopes must be an instance of list')
        self.scopes = scopes
        self.redirect_uri = redirect_uri
        self.show_dialog = show_dialog

        if state is None:
            state = self._create_secret()
        self.state = state

        self.access_token = None  # For client credentials oauth flow
        self.expiry = None  # For client credentials oauth flow

        def load_from_env(self):
            self.client_id = os.environ['SPOTIFY_CLIENT_ID']
            self.client_secret = os.environ['SPOTIFY_CLIENT_SECRET']
            self.redirect_uri = os.environ['SPOTIFY_REDIRECT_URI']

    @property
    def is_oauth_ready(self):
        if self.client_id and self.redirect_uri and self.scopes and self.state and self.show_dialog is not None:
            return True
        return False


class UserCredentials(_Creds):
    ''' minimum requirements: user_id and access_token for functional user'''
    def __init__(self, access_token=None, refresh_token=None, scopes=[], expiry=None, user_id=None, state=None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expiry = expiry  # expiry date. Not to be confused with expires in
        self.user_id = user_id

        if not isinstance(scopes, list):
            raise TypeError('Scopes must be an instance of list')
        self.scopes = scopes

        if state is None:
            state = self._create_secret()
        self.state = state


class Client:
    def __init__(self, client_creds=None, user_creds=None, ensure_user_auth=False, proxies={}, timeout=4, max_retries=10, default_limit=100):
        # Two main credentials model
        self.client_creds = client_creds
        self._user_creds = user_creds

        # Requests defaults
        self._session = Session()  # Using session for better performance (connection pooling) and setting standard request properties with ease
        self.proxies = proxies  # http://docs.python-requests.org/en/master/user/advanced/#proxies & http://docs.python-requests.org/en/master/user/advanced/#socks
        self.timeout = timeout
        self.max_retries = max_retries

        # Api defaults
        self.default_limit = default_limit

        # Client state
        self.client_authenticated = False  # For client credentials oauth flow
        self.user_authenticated = False
        self.caller = None  # manually change this flag to either client_creds object or user_creds object to communicate with API as client or as user

        # Others
        self.ensure_user_auth = ensure_user_auth
        if user_creds and client_creds and ensure_user_auth:  # Attempt user authorization upon client instantiation
            self.caller = self._user_creds
            self._check_authorization()

    def _check_authorization(self):
        ''' checks whether the credentials provided are valid or not by making and api call that requires no scope but still requires authorization '''
        test_url = BASE_URI + 'search?q=Hey%20spotify%2C%20am%20I%20authorized%3F&type=artist'
        try:
            self._send_authorized_request(Request(test_url))
        except AuthError as e:
            raise e

    def _send_authorized_request(self, r):
        self._session.prep
        # Take care of http 429 error (retry after) use the: 'Retry-After' header for no. of seconds to wait before the next request should be sent
        # Take care of refresh token in case expired
        # Take care of timeouts
        try:
            r.raise_for_status()
        except:
            pass

    def refresh_token():
        if self.caller is self.user_creds:
            return self._refresh_user_token()
        else:
            return self.authorize_client_creds()

    def _refresh_user_token(self):
        pass

    def authorize_client_creds(self):
        ''' Authorize with client credentials i.e. Only with client secret and client id.
            This will give you limited functionality '''
        pass

    @property
    def user_creds(self):
        return self._user_creds

    @user_creds.setter
    def user_creds(self, user_creds):
        ''' if user is set, do: '''
        self._user_creds = user_creds
        if self.ensure_user_auth:
            self.caller = self._user_creds
            self._check_authorization()

    @property
    def oauth_uri(self):
        ''' Generate OAuth URI for authentication '''
        if self.client_creds.is_oauth_ready:
            params = {
                'client_id': self.client_creds.client_id,
                'response_type': 'code',
                'redirect_uri': self.client_creds.redirect_uri,
                'scopes': ' '.join(self.client_creds.scopes),
                'state': self.client_creds.state
            }
            params = parse.urlencode(params)
            return f'{OAUTH_AUTHORIZE_URL}?{params}'

    @property
    def is_active(self):
        ''' Check if user_creds are valid '''
        if self.caller is None:
            return False
        try:
            self._check_authorization()
        except AuthError:
            return False
        else:
            return True

    def authorize_with_grant(grant):
        ''' Part of OAuth authorization code flow
            Sets a user_creds model if successful
            Raises an error if not successful '''
        pass

    @staticmethod
    def _convert_iso_date(iso_date):
        ''' Converts  ISO 8601 UTC date format to python datetime object '''
        pass

    @property
    def _content_type_header(self):
        return {'Content-Type': 'application/json'}

    @property
    def _authorization_header(self):
        if self.caller:
            return {'Authorization': 'Bearer {}'.format(self.caller.access_token)}
