import os
import sys
import json
import socket
import base64
import pprint
import pickle
import secrets
import logging
import datetime
from time import sleep
from urllib import parse

from requests import Request, Session, Response
from requests.exceptions import HTTPError, Timeout, ProxyError, RetryError
from requests.adapters import HTTPAdapter

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

_DEBUG = False
BACKOFF_INCREMENT = 0.4  # seconds
BACKOFF_EXPONENT = 1.2
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
HOST_NAME = socket.gethostname()
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
    'user-library-read',  # Library
    'user-library-modify',
    'user-top-read',  # Listening History
    'user-read-recently-played'
]


logger = logging.getLogger(__name__)


# TODO: Implement cache https://developer.spotify.com/documentation/web-api/#conditional-requests
# TODO: Check client._caller flow
# TODO: Test refresh tokens


class SpotifyError(Exception):
    ''' RFC errors https://tools.ietf.org/html/rfc6749#section-5.2 '''
    def _build_super_msg(self, msg, http_res, e):
        return {
            'msg': msg,
            'http_response': http_res,
            'original exception': e
        }


class ApiError(SpotifyError):
    def __init__(self, msg, http_response=None, e=None):
        ''' https://developer.spotify.com/documentation/web-api/#response-schema // regular error object '''
        self.msg = msg
        self.http_response = http_response
        self.code = getattr(http_response, 'status_code', None)
        super_msg = self._build_super_msg(msg, http_response, e)
        super(ApiError, self).__init__(super_msg)


class AuthError(SpotifyError):
    ''' https://developer.spotify.com/documentation/web-api/#response-schema // authentication error object '''
    def __init__(self, msg, http_response=None, e=None):
        self.msg = msg
        self.http_response = http_response
        self.code = getattr(http_response, 'status_code', None)
        super_msg = self._build_super_msg(msg, http_response, e)
        super(AuthError, self).__init__(super_msg)


class _Creds:
    def __init__(self, *args, **kwargs):
        raise TypeError('_Creds class isn\'nt calleable')

    def save_to_file(self, path=CURRENT_DIR, name=None):
        if name is None:
            name = HOST_NAME + "_" + "Spotify_" + self.__class__.__name__
        path = os.path.join(path, name)
        with open(path, 'wb') as creds_file:
            pickle.dump(self, creds_file, pickle.HIGHEST_PROTOCOL)

    def load_from_file(self, path=CURRENT_DIR, name=None):
        if name is None:
            name = HOST_NAME + "_" + "Spotify_" + self.__class__.__name__
        path = os.path.join(path, name)
        with open(path, 'rb') as creds_file:
            self = pickle.load(creds_file)

    def _delete_pickle(self, path=CURRENT_DIR, name=None):
        ''' BE CAREFUL!! THIS WILL PERMENANTLY DELETE ONE OF YOUR FILES IF USED INCORRECTLY
            It is recommended you leave the defaults if you're using this library for personal use only '''
        if name is None:
            name = HOST_NAME + "_" + "Spotify_" + self.__class__.__name__
        path = os.path.join(path, name)
        os.remove(path)

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

    @staticmethod
    def _create_secret(bytes_length=32):
        return secrets.base64.standard_b64encode(secrets.token_bytes(bytes_length)).decode('utf-8')


def _set_empty_user_creds_if_none(f):
    def innermost(*args, **kwargs):
        self = args[0]
        if self.user_creds is None:
            self._user_creds = UserCredentials()
        self._caller = self.user_creds
        return f(*args, **kwargs)
    return innermost


class Client:
    def __init__(self, client_creds=None, user_creds=None, ensure_user_auth=False, proxies={}, timeout=4, max_retries=10, enforce_state_check=True):
        # The two main credentials model
        if client_creds is None:
            self.client_creds = ClientCredentials()
        else:
            self.client_creds = client_creds
        self._user_creds = user_creds

        # Request defaults
        self.timeout = timeout  # Seconds before request raises a timeout error
        self.max_retries = max_retries  # Max retries when an HTTP error occurs
        self._session = self._create_session(max_retries, proxies)  # Using session for better performance (connection pooling) and setting standard request properties with ease

        # Api defaults
        self.enforce_state_check = enforce_state_check  # Check for a CSRF-token-like string. Helps verifying the identity of a callback sender thus avoiding CSRF attacks. Optional

        # You shouldn't need to manually change this flag.
        # It's set to be equal to either the client_creds object or user_creds object depending on which was last authorized
        self._caller = None

        # Others
        self.ensure_user_auth = ensure_user_auth
        if hasattr(user_creds, 'access_token') and ensure_user_auth:  # Attempt user authorization upon client instantiation
            self._caller = self._user_creds
            self._check_authorization()

    def _create_session(self, max_retries, proxies):
        sess = Session()
        http_adapter = HTTPAdapter(max_retries=max_retries)
        sess.mount('http://', http_adapter)
        sess.mount('https://', http_adapter)
        sess.proxies.update(proxies)  # http://docs.python-requests.org/en/master/user/advanced/#proxies & http://docs.python-requests.org/en/master/user/advanced/#socks
        return sess

    def _check_authorization(self):
        ''' checks whether the credentials provided are valid or not by making and api call that requires no scope but still requires authorization '''
        test_url = BASE_URI + 'search?q=' + parse.urlencode(dict(q='Hey spotify am I authorized', type='artist'))  # Hey%20spotify%2C%20am%20I%20authorized%3F&type=artist'
        try:
            self._send_authorized_request(Request(method='GET', url=test_url))
        except AuthError as e:
            raise e

    def _send_authorized_request(self, r):
        if self._caller.access_is_expired:  # True if expired and None if there's no expiry set
            self.refresh_token()
        r.headers.update(self._access_authorization_header)
        return self._send_request(r)

    def _send_request(self, r):
        current_sleep_period = BACKOFF_INCREMENT
        requests_attempted = 0

        try:
            requests_attempted += 1
            prepped = r.prepare()
            if _DEBUG:
                pprint.pprint(r.headers)
                pprint.pprint(r.data)
            res = self._session.send(prepped, timeout=self.timeout)
            if _DEBUG:
                pprint.pprint(res.__dict__)
            res.raise_for_status()
        except Timeout as e:
            raise ApiError('Request timed out.\nTry increasing the client\'s timeout period', http_response=res, e=e)
        except HTTPError as e:
            if res.status_code == 429:  # If too many requests
                while requests_attempted < self.max_retries:
                    sleep(current_sleep_period)
                    current_sleep_period += (BACKOFF_INCREMENT * BACKOFF_EXPONENT)
                    self._send_request(r)
            elif res.status_code == 401:
                if res.json().get('error', None) == 'The access token expired':
                    self._refresh_token()
                    self._send_request(r)
                else:
                    msg = res.json().get('error_description', None) or res.json()
                    raise AuthError(msg=msg, http_response=res)  # Or use error for a less verbose error
            else:
                msg = res.json()
                raise ApiError(msg=msg, http_response=res, e=e)
        else:
            return res

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
        res = self._send_request(Request(method='POST', url=OAUTH_TOKEN_URL, headers=headers, data=data)).json()
        new_creds_obj = self._user_json_to_object(res)
        self._update_user_creds_with(new_creds_obj)

    def authorize_client_creds(self):
        ''' https://developer.spotify.com/documentation/general/guides/authorization-guide/ 
            Authorize with client credentials i.e. Only with client secret and client id.
            This will give you limited functionality '''
        if self.client_creds and self.client_creds.client_id and self.client_creds.client_secret:
            data = {
                'grant_type': 'client_credentials'
            }
            headers = self._client_authorization_header
            try:
                res = self._send_request(Request(method='POST', url=OAUTH_TOKEN_URL, headers=headers, data=data))
            except ApiError as e:
                raise AuthError(msg='Failed to authenticate with client credentials', http_response=e.http_response, e=e)
            else:
                new_creds_json = res.json()
                new_creds = self._client_json_to_object(new_creds_json)
                self._update_client_creds_with(new_creds)
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
    def is_oauth_ready(self):
        return self.client_creds.is_oauth_ready

    @property
    @_set_empty_user_creds_if_none
    def oauth_uri(self):
        ''' Generate OAuth URI for authentication '''
        #self._create_user_creds_if_none()
        params = {
            'client_id': self.client_creds.client_id,
            'response_type': 'code',
            'redirect_uri': self.client_creds.redirect_uri,
            'scopes': ' '.join(self.client_creds.scopes),
        }
        if self.enforce_state_check and self.user_creds.state:
            params.update({'state': self.user_creds.state})
        params = parse.urlencode(params)
        return f'{OAUTH_AUTHORIZE_URL}?{params}'

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

    def _refresh_token(self):
        if self._caller == self.user_creds:
            self._refresh_user_token()
        elif self._caller == self.client_creds:
            self.authorize_client_creds()

    @_set_empty_user_creds_if_none
    def build_user_credentials(self, grant, state=None, set_user_creds=True, update_user_creds=False, fetch_user_id=True):
        ''' Part of OAuth authorization code flow
            Sets a user_creds model if successful
            Raises an error if not successful '''
        # Check for equality of states
        if state is not None:
            if state != getattr(self.user_creds, 'state', None):
                res = Response()
                res.status_code = 401
                raise AuthError(msg='States do not match or state not provided', http_response=res)
        # Get user creds
        user_creds_json = self._request_user_creds(grant).json()
        new_user_creds = self._user_json_to_object(user_creds_json)
        # Update user id
        if fetch_user_id:
            id_ = self._request_user_id(new_user_creds)
            new_user_creds.user_id = id_
        # Update user creds
        if update_user_creds and set_user_creds:
            self._update_user_creds_with(new_user_creds)
            return self.user_creds
        # Set user creds
        if set_user_creds:
            return self.user_creds
        return new_user_creds

    def _request_user_creds(self, grant):
        data = {
            'grant_type': 'authorization_code',
            'code': grant,
            'redirect_uri': self.client_creds.redirect_uri
        }
        headers = {**self._client_authorization_header, **self._form_url_encoded_type_header}
        return self._send_request(Request(method='POST', url=OAUTH_TOKEN_URL, headers=headers, data=data))

    def _request_user_id(self, user_creds):
        ''' not using self.me as it uses the _send_authorized_request which generates its auth headers from self._caller
        The developer won't necessarily need to set the user credentials after building them ''' 
        header = {'Authorization': 'Bearer {}'.format(user_creds.access_token)}
        url = BASE_URI + 'me'
        res = self._send_request(Request(method='GET', url=url, headers=header)).json()
        return res['id']

    def _update_user_creds_with(self, user_creds_object):
        self.user_creds.__dict__.update(user_creds_object.__dict__)

    def _update_client_creds_with(self, client_creds_object):
        self.client_creds.__dict__.update(client_creds_object.__dict__)

    def _user_json_to_object(self, json_response):
        return UserCredentials(
            access_token=json_response['access_token'],
            scopes=json_response['scope'].split(' '),
            expiry=datetime.datetime.now() + datetime.timedelta(seconds=json_response['expires_in']),
            refresh_token=json_response['refresh_token']
        )

    def _client_json_to_object(self, json_response):
        creds = ClientCredentials()
        creds.access_token = json_response['access_token']
        creds.expiry = datetime.datetime.now() + datetime.timedelta(seconds=json_response['expires_in'])
        return creds

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
        # Took me a whole day to figure out that the colon is supposed to be encoded :'(
        utf_header = self.client_creds.client_id + ':' + self.client_creds.client_secret
        return {'Authorization': 'Basic {}'.format(base64.b64encode(utf_header.encode()).decode())}

    @property
    def _client_authorization_data(self):
        return {
            'client_id': self.client_creds.client_id,
            'client_sectet': self.client_creds.client_secret
        }

    @property
    def _access_authorization_header(self):
        if self._caller:
            return {'Authorization': 'Bearer {}'.format(self._caller.access_token)}
        else:
            raise ApiError(msg='Call Requires an authorized caller, either client or user')

    ############################################################### RESOURCES ###################################################################

    @property
    def me(self):
        r = Request(method='GET', url=BASE_URI + 'me')
        return self._send_authorized_request(r).json()

    @property
    def playlists(self):
        r = Request(method='GET', url=BASE_URI + 'me/playlists')
        return self._send_authorized_request(r).json()

    @property
    def tracks(self):
        r = Request(method='GET', url=BASE_URI + 'me/tracks')
        return self._send_authorized_request(r).json()

    @property
    def random_tracks(self):
        r = Request(method='GET', url=BASE_URI + 'tracks')
        return self._send_authorized_request(r).json()