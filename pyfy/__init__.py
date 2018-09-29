import os
import sys
import json
import base64
import secrets
import logging
import datetime
from time import sleep
from urllib import parse

from requests import Request, Session
from requests.exceptions import HTTPError, Timeout, ProxyError, RetryError

__name__ = 'pyfy'
__about__ = "Lightweight python wrapper for Spotify's web API"
__url__ = 'https://github.com/omarryhan/spyfy'
__version_info__ = ('0', '0', '3d')
__version__ = '.'.join(__version_info__)
__author__ = 'Omar Ryhan'
__author_email__ = 'omarryhan@gmail.com'
__maintainer__ = 'Omar Ryhan'
__license__ = 'MIT'
__copyright__ = '(c) 2018 by Omar Ryhan'
__all__ = [
    'SpotifyError',
    'ApiError',
    'AuthError',
    'ClientCredentials',
    'UserCredentials',
    'Client'
]

BACKING_OFF_INCREMENT = 0.4  # seconds
BACKING_OFF_EXPONENT = 1.2
BASE_URI = 'https://api.spotify.com/v1/'
OAUTH_TOKEN_URL = 'https://accounts.spotify.com/api/token'
OAUTH_AUTHORIZE_URL = 'https://accounts.spotify.com/authorize'
ALL_SCOPES = [
    'streaming',  # Playback
    'app-remote-control',
    'user-follow-modify',  # Follow
    'user-follow-read',
    'playlist-read-private',  # Playlists
    'playlist-modify-private',
    'playlist-read-collaborative',
    'playlist-modify-public',
    'user-modify-playback-state',  # Spotify Connect
    'user-read-playback-state',
    'user-read-currently-playing',
    'user-read-private',  # Users
    'user-read-birthdate',
    'user-read-email',
    'user-library-read',  #  Library
    'user-library-modify',
    'user-top-read',  # Listening History
    'user-read-recently-played'
]

logger = logging.getLogger(__name__)


# TODO: Set session params upon authenticating
# TODO: Implement cache https://developer.spotify.com/documentation/web-api/#conditional-requests

class SpotifyError(Exception):
    pass


class ApiError(SpotifyError):
    def __init__(self, msg, http_response=None, e=None):
        self.http_response = http_response
        self.code = getattr(http_response, 'status_code', None)
        self.msg = msg
        self.original_exception = e
        if e:
            super_msg = msg + f'\nOriginal exception: {e}'
        else:
            super_msg = msg
        super(ApiError, self).__init__(super_msg)


class AuthError(SpotifyError):
    def __init__(self, msg, http_response=None):
        self.http_response = http_response
        self.msg = msg
        self.code = getattr(http_response, 'status_code', None)
        super(AuthError, self).__init__(msg + '\nHTTP error:\n' + http_response.json())


class _Creds:
    def __init__(self, *args, **kwargs):
        raise TypeError('_Creds class isn\'nt calleable')

    def load_from_file(self, path):
        pass

    def save_to_file(self, path):
        pass

    def _create_secret(self, bytes_length=32):
        return secrets.base64.standard_b64encode(secrets.token_bytes(bytes_length)).decode('utf-8')

    @property
    def access_is_expired(self):
        if self.expiry is datetime.datetime:
            return (self.expiry <= datetime.datetime.now())


class ClientCredentials(_Creds):
    def __init__(self, client_id=None, client_secret=None, scopes=ALL_SCOPES, redirect_uri='http://localhost', show_dialog='false'):
        self.client_id = client_id
        self.client_secret = client_secret
        if not isinstance(scopes, list):
            raise TypeError('Scopes must be an instance of list')
        self.scopes = scopes
        self.redirect_uri = redirect_uri
        self.show_dialog = show_dialog

        self.access_token = None  # For client credentials oauth flow
        self.expiry = None  # For client credentials oauth flow

    def load_from_env(self):
        self.client_id = os.environ['SPOTIFY_CLIENT_ID']
        self.client_secret = os.environ['SPOTIFY_CLIENT_SECRET']
        self.redirect_uri = os.environ['SPOTIFY_REDIRECT_URI']

    @property
    def is_oauth_ready(self):
        if self.client_id and self.redirect_uri and self.scopes and self.show_dialog is not None:
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

    def load_from_env(self):
        self.access_token = os.environ['SPOTIFY_ACCESS_TOKEN']
        self.user_id = os.environ['SPOTIFY_USER_ID']


class Client:
    def __init__(self, client_creds=None, user_creds=None, ensure_user_auth=False, proxies={}, timeout=4, max_retries=10, default_limit=100, check_for_state=True):
        # Two main credentials model
        self.client_creds = client_creds
        if user_creds is None:
            self._user_creds = UserCredentials()
        else:
            self._user_creds = user_creds

        # Requests defaults
        self._session = Session()  # Using session for better performance (connection pooling) and setting standard request properties with ease
        self.proxies = proxies  # http://docs.python-requests.org/en/master/user/advanced/#proxies & http://docs.python-requests.org/en/master/user/advanced/#socks
        self.timeout = timeout
        self.max_retries = max_retries
        self.check_for_state = check_for_state

        # Api defaults
        self.default_limit = default_limit  # Resource get limit

        # You shouldn't need to manually change this flag.
        # It's set to be equal to either the client_creds object or user_creds object
        self._caller = None

        # Others
        self.ensure_user_auth = ensure_user_auth
        if user_creds and client_creds and ensure_user_auth:  # Attempt user authorization upon client instantiation
            self._caller = self._user_creds
            self._check_authorization()

    def _check_authorization(self):
        ''' checks whether the credentials provided are valid or not by making and api call that requires no scope but still requires authorization '''
        test_url = BASE_URI + 'search?q=Hey%20spotify%2C%20am%20I%20authorized%3F&type=artist'
        try:
            self._send_authorized_request(Request(test_url))
        except AuthError as e:
            raise e

    def _send_authorized_request(self, r):
        if self._caller.access_is_expired: # True if expired and None if there's no expiry set
            self.refresh_token()
        r.headers.update(self._access_authorization_header)
        return self._send_request(r)

    def _send_request(self, r):
        current_sleep_period = BACKING_OFF_INCREMENT
        requests_attempted = 0

        try:
            requests_attempted += 1
            res = self._session.send(r, proxies=self.proxies, timeout=self.timeout)
            res.raise_for_status()
        except Timeout as e:
            raise ApiError('Request timed out.\nTry increasing the client\'s timeout period', http_response=res, e=e)
        except HTTPError as e:
            if res.status_code == 429:  # If too many requests
                while requests_attempted < self.max_retries:
                    sleep(current_sleep_period)
                    current_sleep_period += (BACKING_OFF_INCREMENT * BACKING_OFF_EXPONENT)
                    self._send_request(r)
            elif res.status_code == 401:
                if res.json().get('error', None) == 'The access token expired':
                    self._refresh_token()
                    self._send_request(r)
                else:
                    raise AuthError(msg=res.json()['error_description'], http_response=res)  # Or use error for a less verbose error
            else:
                msg = res.json().get('message') or res.json().get('error_description') or None
                raise ApiError(msg=msg, http_response=res, e=e)
        else:
            return res.josn()

    def refresh_token(self):
        if self._caller is self.user_creds:
            return self._refresh_user_token()
        elif self._caller is self.client_creds:
            return self.authorize_client_creds()
        else:
            raise AuthError('No token to refresh')

    def _refresh_user_token(self):
        if not self.user_creds.refresh_token:
            raise AuthError(msg='Access token expired and couldn\'t find a refresh token to refresh it')
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.user_creds.refresh_token
        }
        headers = {**self._client_authorization_header, **self._form_url_encoded_type_header}
        self._send_request(Request(method='POST', url=OAUTH_TOKEN_URL, headers=headers, data=data))

    def authorize_client_creds(self):
        ''' Authorize with client credentials i.e. Only with client secret and client id.
            This will give you limited functionality '''
        if self.client_creds:
            data = {
                'grant_type': 'client_credentials'
            }
            headers = self._client_authorization_header
            self._send_request(Request(method='POST', url=OAUTH_TOKEN_URL, headers=headers, data=data))
            self._caller = self.client_creds
            self._check_authorization()
        else:
            raise AuthError('No client credentials set')

    @property
    def user_creds(self):
        return self._user_creds

    @user_creds.setter
    def user_creds(self, user_creds):
        ''' if user is set, do: '''
        self._user_creds = user_creds
        if self.ensure_user_auth:
            self._caller = self._user_creds
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
            }
            if self.check_for_state and self.user_creds.state:
                params.update({'state': self.user_creds.state})
            params = parse.urlencode(params)
            return f'{OAUTH_AUTHORIZE_URL}?{params}'
        else:
            print('')

    @property
    def is_active(self):
        ''' Check if user_creds are valid '''
        if self._caller is None:
            return False
        try:
            self._check_authorization()
        except AuthError:
            return False
        else:
            return True

    def _request_client_creds(self, grant):
        data = {
            'grant_type': 'authorization_code',
            'code': grant,
            'redirect_uri': self.client_creds.redirect_uri
        }
        headers = self._client_authorization_header
        return self._send_request(Request(method='POST', url=OAUTH_TOKEN_URL, headers=headers, data=data))

    def _refresh_token(self):
        if self._caller == self.user_creds:
            self._refresh_user_token()
        elif self._caller == self.client_creds:
            self.authorize_client_creds()

    def build_user_credentials(self, grant, state=None, update_user_creds=True):
        ''' Part of OAuth authorization code flow
            Sets a user_creds model if successful
            Raises an error if not successful '''
        # Check for equality of states
        if state is not None and self.user_creds.state is not None:
            if state != self.user_creds.state:
                raise AuthError(msg='States do not match')
        # Get user creds
        data = {
            'grant_type': 'authorization_code',
            'code': grant,
            'redirect_uri': self.client_creds.redirect_uri
        }
        headers = self._client_authorization_header
        res = self._send_request(Request(method='POST', url=OAUTH_TOKEN_URL, headers=headers, data=data))
        new_user_creds = self._user_json_to_object(res.json())
        # Set user creds
        if update_user_creds:
            self._update_user_creds_with(new_user_creds)
            return self.user_creds
        return new_user_creds

    def _update_user_creds_with(self, user_creds_object):
        self.user_creds.__dict__.update(user_creds_object.__dict__)

    def _user_json_to_object(self, json_response):
        return UserCredentials(
            access_token=json_response['access_token'],
            scopes=json_response['scope'].split(' '),
            expiry=datetime.datetime.now() + datetime.timedelta(seconds=json_response['expires_in']),
            refresh_token=json_response['refresh_token']
        )

    @staticmethod
    def _convert_iso_date(iso_date):
        ''' Converts  ISO 8601 UTC date format to python datetime object '''
        pass

    @property
    def _json_content_type_header(self):
        return {'Content-Type': 'application/json'}

    @property
    def _form_url_encoded_type_header(self):
        return {'Content-Type': 'application/x-www-form-urlencoded'}

    @property
    def _client_authorization_header(self):
        return {'Authorization': 'Basic {}:{}'.format(
            base64.b64encode(self.client_creds.client_id.encode('utf-8')),
            base64.b64encode(self.client_creds.client_secret.encode('utf-8')))
        }

    @property
    def _access_authorization_header(self):
        if self._caller:
            return {'Authorization': 'Bearer {}'.format(self._caller.access_token)}
