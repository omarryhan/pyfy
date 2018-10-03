import os
import sys
import json
import socket
import base64
import pprint
import pickle
import secrets
import logging
import warnings
import datetime
from time import sleep
from urllib import parse
from functools import wraps
from json.decoder import JSONDecodeError

from requests import Request, Session, Response
from requests.exceptions import HTTPError, Timeout, ProxyError, RetryError
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util import Retry

__name__ = 'pyfy'
__about__ = "Lightweight python wrapper for Spotify's web API"
__url__ = 'https://github.com/omarryhan/spyfy'
__version_info__ = ('0', '0', '4b')
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
    'ClientCreds',
    'UserCreds',
    'Client'
]

try:
    DEFAULT_FILENAME_BASE = socket.gethostname() + "_" + "Spotify_"
except:
    DEFAULT_FILENAME_BASE = 'Spotify_'
TOKEN_EXPIRED_MSG = 'The access token expired'  # Msg sent back when token is expired
_DEBUG = False  # If true, client will log every request and response in a pretty printed format
BASE_URI = 'https://api.spotify.com/v1'
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
if _DEBUG:
    logger.setLevel(logging.DEBUG)


# TODO: Implement cache https://developer.spotify.com/documentation/web-api/#conditional-requests
# TODO: Check client._caller flow
# TODO: Test client always raises an error if not http 2**
# TODO: Revoke token

    ####################################################################### EXCEPTIONS ############################################################################

class SpotifyError(Exception):
    ''' RFC errors https://tools.ietf.org/html/rfc6749#section-5.2 '''
    def _build_super_msg(self, msg, http_res, http_req, e):
        if not http_req and not http_res and not e:
            return msg
        elif getattr(http_res, 'status_code', None) == 400 and http_req:  # If bad request or not found, show url and data
            body = http_req.data or http_req.json
            return '\nError msg: {}\nHTTP Error: 400-Bad request\nRequest URL: {}\nRequest body: {}\nRequest headers: {}'.format(
                msg,
                http_req.url, pprint.pformat(body),
                pprint.pformat(http_req.headers)
            )
        elif getattr(http_res, 'status_code', None) == 401 and http_req:  # If unauthorized, only show headers
            return '\nError msg: {}\nHTTP Error: {}.\nRequest headers: {}'.format(
                msg,
                http_res.status_code,
                pprint.pformat(http_req.headers)
            )
        elif getattr(http_res, 'status_code', None) == 403 and http_req:  # If bad request or not found, show url and data
            body = http_req.data or http_req.json
            return '\nError msg: {}\nHTTP Error: 403-Forbidden\nRequest URL: {}\nRequest body: {}\nRequest headers: {}'.format(
                msg,
                http_req.url, pprint.pformat(body),
                pprint.pformat(http_req.headers)
            )
        elif getattr(http_res, 'status_code', None) == 404 and http_req:  # If bad request or not found, show url and data
            body = http_req.data or http_req.json
            return '\nError msg: {}\nHTTP Error: 404-Resource not found\nRequest URL: {}\nRequest body: {}'.format(
                msg,
                http_req.url, pprint.pformat(body)
            )
        return {
            'msg': msg,
            'http_response': http_res.__dict__,
            'http_request': http_req.__dict__,
            'original exception': e
        }


class ApiError(SpotifyError):
    def __init__(self, msg, http_response=None, http_request=None, e=None):
        ''' https://developer.spotify.com/documentation/web-api/#response-schema // regular error object '''
        self.msg = msg
        self.http_response = http_response
        self.http_request = http_request
        self.code = getattr(http_response, 'status_code', None)
        super_msg = self._build_super_msg(msg, http_response, http_request, e)
        super(ApiError, self).__init__(super_msg)


class AuthError(SpotifyError):
    ''' https://developer.spotify.com/documentation/web-api/#response-schema // authentication error object '''
    def __init__(self, msg, http_response=None, http_request=None, e=None):
        self.msg = msg
        self.http_response = http_response
        self.http_request = http_request
        self.code = getattr(http_response, 'status_code', None)
        super_msg = self._build_super_msg(msg, http_response, http_request, e)
        super(AuthError, self).__init__(super_msg)

    ####################################################################### HELPERS & WRAPPERS ############################################################################

def _create_secret(bytes_length=32):
    return secrets.base64.standard_b64encode(secrets.token_bytes(bytes_length)).decode('utf-8')


def _set_empty_user_creds_if_none(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        self = args[0]
        if self.user_creds is None:
            self._user_creds = UserCreds()
        self._caller = self.user_creds
        return f(*args, **kwargs)
    return wrapper


def _set_empty_client_creds_if_none(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        self = args[0]
        if self.client_creds is None:
            self.client_creds = ClientCreds()
        return f(*args, **kwargs)
    return wrapper


def _require_user_id(*args, plural=None):
    ''' wrapper that injects current user_id in a given method, given user has one and also given user doesn't pass one.
    Set plural to true if the user_id parameter is user_ids '''
    def outer_wrapper(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if plural is None:
                argument_name = 'user_id'
            elif plural is True:
                argument_name = 'user_ids'
            if kwargs.get(argument_name, None): # If user provided an ID, run thr function without changing anything
                return f(*args, **kwargs)
            self = args[0]
            if not self.user_creds.user_id and self.user_creds.access_token:
                id_ = self._request_user_id(self.user_creds)
                self.user_creds.user_id = id_
            if plural is True:
                return f(*args, **kwargs, user_ids=self.user_creds.user_id) 
            return f(*args, **kwargs, user_id=self.user_creds.user_id)
        return wrapper
    if plural is None and args:  # If decorator wasn't called, return default (user_id) not (user_ids)
        return outer_wrapper(args[0])
    return outer_wrapper


def _safe_get(dct, *keys):
    for key in keys:
        try:
            dct = dct[key]
        except (KeyError, TypeError):
            return None
    return dct


def _locale_injectable(argument_name, support_from_token=True):  # market or country
    ''' Injects user's locale if applicable. Only supports one input, either market or country (interchangeable) '''
    def outer_wrapper(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if kwargs.get(argument_name) is None:  # If user didn't assign to the parameter, inject
                self = args[0]
                if self.default_to_local_country is True and self._caller == self.user_creds:  # if caller is a user not client.
                    if support_from_token:  # some endpoints do not support 'from_token' as a country/market parameter. EDIT: apparently it's working now. I'm keeping it anyway
                        injection = 'from_token'
                    else:
                        injection = self.me.get('country')  # For some reason, countries are often not returned by the API
                    if argument_name == 'market':
                        return f(*args, **kwargs, market=injection)
                    elif argument_name == 'country':
                        return f(*args, **kwargs, country=injection)
                    else:
                        raise TypeError('Market injectable parameter should be either market or country')
                else:
                    return f(*args, **kwargs)
            else:
                return f(*args, **kwargs)
        return wrapper
    return outer_wrapper


def _nullable_response(f):
    ''' wrapper that return an empty dict instead of a None body, that causes json.loads to raise a ValueError (JSONDecodeError) '''
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            original_response = f(*args, **kwargs)
        except JSONDecodeError:
            return {}
        else:
            return original_response
    return wrapper

    ####################################################################### CREDENTIALS ############################################################################

class _Creds:
    def __init__(self, *args, **kwargs):
        raise TypeError('_Creds class isn\'nt calleable')

    def pickle(self, path=os.path.dirname(os.path.abspath(__file__)), name=None):
        if name is None:
            name = DEFAULT_FILENAME_BASE + self.__class__.__name__ + '_pickle'
        path = os.path.join(path, name)
        with open(path, 'wb') as creds_file:
            pickle.dump(self, creds_file, pickle.HIGHEST_PROTOCOL)

    # Unpickling doesn't work by setting an instance's (self) to an output of one of its own methods. Apparently, the method must be external 
    #def unpickle(self, path=os.path.dirname(os.path.abspath(__file__)), name=None):
    #    if name is None:
    #        name = DEFAULT_FILENAME_BASE + self.__class__.__name__ + '_pickle'
    #    path = os.path.join(path, name)
    #    with open(path, 'rb') as creds_file:
    #        self = pickle.load(creds_file)

    def _delete_pickle(self, path=os.path.dirname(os.path.abspath(__file__)), name=None):
        ''' BE CAREFUL!! THIS WILL PERMENANTLY DELETE ONE OF YOUR FILES IF USED INCORRECTLY
            It is recommended you leave the defaults if you're using this library for personal use only '''
        if name is None:
            name = DEFAULT_FILENAME_BASE + self.__class__.__name__ + '_pickle'
        path = os.path.join(path, name)
        os.remove(path)

    def save_as_json(self, path=os.path.dirname(os.path.abspath(__file__)), name=None):
        if name is None:
            name = DEFAULT_FILENAME_BASE + self.__class__.__name__ + '.json'
        path = os.path.join(path, name)
        with open(path, 'w') as outfile:
            json.dump(self.__dict__, outfile)

    def load_from_json(self, path=os.path.dirname(os.path.abspath(__file__)), name=None):
        if name is None:
            name = DEFAULT_FILENAME_BASE + self.__class__.__name__ + '.json'
        path = os.path.join(path, name)
        with open(path, 'r') as infile:
            self.__dict__.update(json.load(infile))

    def _delete_json(self, path=os.path.dirname(os.path.abspath(__file__)), name=None):
        if name is None:
            name = DEFAULT_FILENAME_BASE + self.__class__.__name__ + '.json'
        path = os.path.join(path, name)
        os.remove(path)

    @property
    def access_is_expired(self):
        if isinstance(self.expiry, datetime.datetime):
            return (self.expiry <= datetime.datetime.now())
        return None


class ClientCreds(_Creds):
    def __init__(self, client_id=None, client_secret=None, scopes=ALL_SCOPES, redirect_uri='http://localhost', show_dialog=False):
        '''
        Parameters:
            show_dialog: if set to false, Spotify will not show a new authentication request if user already authorized the client
        '''
        self.client_id = client_id
        self.client_secret = client_secret
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


class UserCreds(_Creds):
    def __init__(self, access_token=None, refresh_token=None, scopes=[], expiry=None, user_id=None, state=_create_secret()):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expiry = expiry  # expiry date. Not to be confused with expires in
        self.user_id = user_id
        self.state = state

    def load_from_env(self):
        self.access_token = os.environ['SPOTIFY_ACCESS_TOKEN']
        self.refresh_token = os.getenv('SPOTIFY_REFRESH_TOKEN', None)

    ####################################################################### CLIENT ############################################################################

class Spotify:
    def __init__(self, client_creds=ClientCreds(), user_creds=None, ensure_user_auth=False, proxies={}, timeout=7, max_retries=10, enforce_state_check=True, backoff_factor=0.1, default_to_local_country=True):
        '''
        Parameters:
            client_creds: A client credentials model
            user_creds: A user credentials model
            ensure_user_auth: Whether or not to fail if user_creds provided where invalid and not refresheable
            proxies: socks or http proxies # http://docs.python-requests.org/en/master/user/advanced/#proxies & http://docs.python-requests.org/en/master/user/advanced/#socks
            timeout: Seconds before request raises a timeout error
            max_retries: Max retries before a request fails
            enforce_state_check: Check for a CSRF-token-like string. Helps verifying the identity of a callback sender thus avoiding CSRF attacks. Optional
        '''
        # The two main credentials model
        self.client_creds = client_creds
        self._user_creds = user_creds

        # Request defaults
        self.timeout = timeout
        self._session = self._create_session(max_retries, proxies, backoff_factor)

        # Api defaults
        self.enforce_state_check = enforce_state_check

        # You shouldn't need to manually change this flag.from_token
        # It's bound to be equal to either the client_creds object or user_creds object depending on which was last authorized
        self._caller = None

        self.ensure_user_auth = ensure_user_auth
        self.default_to_local_country = default_to_local_country
        if hasattr(user_creds, 'access_token') and ensure_user_auth:  # Attempt user authorization upon client instantiation
            self._caller = self._user_creds
            self._check_authorization()

    def _create_session(self, max_retries, proxies, backoff_factor):
        sess = Session()
        # Retry only on idemportent requests and only when too many requests
        retries = Retry(total=max_retries, backoff_factor=backoff_factor, status_forcelist=[429], method_whitelist=['GET', 'UPDATE', 'DELETE'])
        http_adapter = HTTPAdapter(max_retries=retries)
        sess.mount('http://', http_adapter)
        sess.proxies.update(proxies)  
        return sess

    def _check_authorization(self):
        ''' checks whether the credentials provided are valid or not by making and api call that requires no scope but still requires authorization '''
        test_url = BASE_URI + '/search?' + parse.urlencode(dict(q='Hey spotify am I authorized', type='artist'))  # Hey%20spotify%2C%20am%20I%20authorized%3F&type=artist'
        try:
            self._send_authorized_request(Request(method='GET', url=test_url))
        except AuthError as e:
            raise e

    def _send_authorized_request(self, r):
        if getattr(self._caller, 'access_is_expired', None) is True:  # True if expired and None if there's no expiry set
            self._refresh_token()
        r.headers.update(self._access_authorization_header)
        return self._send_request(r)

    def _send_request(self, r):
        prepped = r.prepare()
        if _DEBUG:
            #pprint.pprint({'REQUEST': r.__dict__})
            logger.debug(pprint.pformat({'REQUEST': r.__dict__}))
        try:
            res = self._session.send(prepped, timeout=self.timeout)
            if _DEBUG:
                #pprint.pprint({'RESPONSE': res.__dict__})
                logger.debug(pprint.pformat({'RESPONSE': res.__dict__}))
            res.raise_for_status()
        except Timeout as e:
            raise ApiError('Request timed out.\nTry increasing the client\'s timeout period', http_response=None, http_request=r, e=e)
        except HTTPError as e:
            #if res.status_code == 429:  # If too many requests
            if res.status_code == 401:
                if res.json().get('error', None).get('message', None) == TOKEN_EXPIRED_MSG:
                    old_auth_header = r.headers['Authorization']
                    self._refresh_token()  # Should either raise an error or refresh the token
                    new_auth_header = self._access_authorization_header
                    assert new_auth_header != old_auth_header  # Assert header is changed to avoid 
                    r.headers.update(new_auth_header)
                    return self._send_request(r)
                else:
                    msg = res.json().get('error_description') or res.json()
                    raise AuthError(msg=msg, http_response=res, http_request=r, e=e)
            else:
                msg = _safe_get(res.json(), 'error', 'message') or _safe_get(res.json(), 'error_description')
                raise ApiError(msg=msg, http_response=res, http_request=r, e=e)
        else:
            return res

    def authorize_client_creds(self, client_creds=None):
        ''' https://developer.spotify.com/documentation/general/guides/authorization-guide/ 
            Authorize with client credentials oauth flow i.e. Only with client secret and client id.
            This will give you limited functionality '''
        if client_creds:
            if self.client_creds:
                warnings.warn('Overwriting existing client_creds object')
            self.client_creds = client_creds
        if not self.client_creds or not self.client_creds.client_id or not self.client_creds.client_secret:
            raise AuthError('No client credentials set')
        data = {'grant_type': 'client_credentials'}
        headers = self._client_authorization_header
        try:
            r = Request(method='POST', url=OAUTH_TOKEN_URL, headers=headers, data=data)
            res = self._send_request(r)
        except ApiError as e:
            raise AuthError(msg='Failed to authenticate with client credentials', http_response=e.http_response, http_request=r, e=e)
        else:
            new_creds_json = res.json()
            new_creds_model = self._client_json_to_object(new_creds_json)
            self._update_client_creds_with(new_creds_model)
            self._caller = self.client_creds
            self._check_authorization()

    @property
    def user_creds(self):
        return self._user_creds

    @user_creds.setter
    def user_creds(self, user_creds):
        ''' if user is set, do: '''
        self._user_creds = user_creds
        self._caller = self._user_creds
        if self.ensure_user_auth:
            self._check_authorization()

    @property
    def is_oauth_ready(self):
        return self.client_creds.is_oauth_ready

    @property
    @_set_empty_user_creds_if_none
    def oauth_uri(self):
        ''' Generate OAuth URI for authentication '''
        params = {
            'client_id': self.client_creds.client_id,
            'response_type': 'code',
            'redirect_uri': self.client_creds.redirect_uri,
            'scopes': ' '.join(self.client_creds.scopes),
            'show_dialog': json.dumps(self.client_creds.show_dialog)
        }
        if self.enforce_state_check:
            if self.user_creds.state is None:
                warnings.warn('No user state provided. Returning URL without a state!')
            else:
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
        if self._caller is self.user_creds:
            return self._refresh_user_token()
        elif self._caller is self.client_creds:
            return self.authorize_client_creds()
        else:
            raise AuthError('No caller to refresh token for')

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

    @_set_empty_user_creds_if_none
    def build_user_credentials(self, grant, state=None, set_user_creds=True, update_user_creds=True, fetch_user_id=True):
        ''' Second part of OAuth authorization code flow, Raises an
            - state: State returned from oauth callback
            - set_user_creds: Whether or not to set the user created to the client as the current active user
            - update_user_creds: If set to yes, it will update the attributes of the client's current user if set. Else, it will overwrite the existing one. Must have set_user_creds as True.
            - fetch_user_id: if yes, it will call the /me endpoint and try to fetch the user id, which will be needed to fetch user owned resources
            '''
        # Check for equality of states
        if state is not None:
            if state != getattr(self.user_creds, 'state', None):
                res = Response()
                res.status_code = 401
                raise AuthError(msg='States do not match or state not provided', http_response=res)

        # Get user creds
        user_creds_json = self._request_user_creds(grant).json()
        user_creds_model = self._user_json_to_object(user_creds_json)

        # Update user id
        if fetch_user_id:
            id_ = self._request_user_id(user_creds_model)
            user_creds_model.user_id = id_

        # Update user creds
        if update_user_creds and set_user_creds:
            self._update_user_creds_with(user_creds_model)
            return self.user_creds

        # Set user creds
        if set_user_creds:
            return self.user_creds
        return user_creds_model

    def _request_user_creds(self, grant):
        data = {
            'grant_type': 'authorization_code',
            'code': grant,
            'redirect_uri': self.client_creds.redirect_uri
        }
        headers = {**self._client_authorization_header, **self._form_url_encoded_type_header}
        return self._send_request(Request(method='POST', url=OAUTH_TOKEN_URL, headers=headers, data=data))

    def _request_user_id(self, user_creds):
        ''' not using client.me as it uses the _send_authorized_request method which generates its auth headers from self._caller attribute.
        The developer won't necessarily need to set the user's credentials as the self._caller after building them. Ergo, the need for this method''' 
        header = {'Authorization': 'Bearer {}'.format(user_creds.access_token)}
        url = BASE_URI + '/me'
        res = self._send_request(Request(method='GET', url=url, headers=header)).json()
        return res['id']

    def _update_user_creds_with(self, user_creds_object):
        for key, value in user_creds_object.__dict__.items():
            if value is not None:
                #if isinstance(value, dict) and isinstance(getattr(self.user_creds, key), dict):  # if dicts, merge
                #    setattr(self.user_creds, key, {**getattr(self.user_creds, key), **value})
                #elif isinstance(value, list) and isinstance(getattr(self.user_creds, key), list):  # if lists, extend
                #    getattr(self.user_creds, key).extend(value)
                #else:
                setattr(self.user_creds, key, value)

    @_set_empty_client_creds_if_none
    def _update_client_creds_with(self, client_creds_object):
        for key, value in client_creds_object.__dict__.items():
            if value is not None:
                setattr(self.client_creds, key, value)

    def _user_json_to_object(self, json_response):
        return UserCreds(
            access_token=json_response['access_token'],
            scopes=json_response['scope'].split(' '),
            expiry=datetime.datetime.now() + datetime.timedelta(seconds=json_response['expires_in']),
            refresh_token=json_response.get('refresh_token', None)
        )

    @staticmethod
    def _client_json_to_object(json_response):
        creds = ClientCreds()
        creds.access_token = json_response['access_token']
        creds.expiry = datetime.datetime.now() + datetime.timedelta(seconds=json_response['expires_in'])
        return creds

    @staticmethod
    def _convert_to_iso_date(date):
        return date.isoformat()
    
    @staticmethod
    def convert_from_iso_date(date):
        if not isinstance(date, datetime.datetime):
            raise TypeError('date must be of type datetime.datetime')
        return datetime.date.fromisoformat(date)
        
    @property
    def _json_content_type_header(self):
        return {'Content-Type': 'application/json'}

    @property
    def _form_url_encoded_type_header(self):
        return {'Content-Type': 'application/x-www-form-urlencoded'}

    @property
    def _client_authorization_header(self):
        if self.client_creds.client_id and self.client_creds.client_secret:
            # Took me a whole day to figure out that the colon is supposed to be encoded :'(
            utf_header = self.client_creds.client_id + ':' + self.client_creds.client_secret
            return {'Authorization': 'Basic {}'.format(base64.b64encode(utf_header.encode()).decode())}
        else:
            raise AttributeError('No client credentials found to make an authorization header')

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


    ################################################################### RESOURCE HELPERS ##############################################################################

    @staticmethod
    def _safe_add_query_param(url, query):
        ''' Removes None variables from query, then attaches it to the original url '''
        # Check if url and query are proper types
        if not isinstance(query, dict) or not isinstance(url, str):
            raise TypeError('Queries must be an instance of a dict and url must be an instance of string in order to be properly encoded')
        # Remove bad params
        bad_params = [None, tuple(), dict(), list()]
        safe_query = {}
        for k, v in query.items():
            if v not in bad_params:
                if type(v) == bool:
                    v = json.dumps(v)
                safe_query[k] = v
        # Add safe query to url
        if safe_query:
            url = url + '?'
        return url + parse.urlencode(safe_query)

    def _json_safe_dict(self, data):
        safe_types = [float, str, int, bool]
        safe_json = {}
        for k, v in data.items():
            if type(v) in safe_types:
                safe_json[k] = v
            elif type(v) == dict and len(v) > 0:
                safe_json[k] = self._json_safe_dict(v)
        return safe_json

    @staticmethod
    def _parametrize_list(list_):
        if type(list_) == list:
            list_ = ','.join(list_)
        return list_

    @staticmethod
    def _is_single_resource(resource):
        if isinstance(resource, str) or (type(resource) == list and len(resource) < 1) or type(resource) == int:  # if int, str or list with one item return True
            return True
        return False

    ####################################################################### RESOURCES ############################################################################

    def _user_playlists(self, limit=None, offset=None):
        url = BASE_URI + '/me/playlists'
        params = dict(limit=limit, offset=offset)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    def user_playlists(self, user_id=None, limit=None, offset=None):
        if user_id is None:
            return self._user_playlists(limit=limit, offset=offset)
        url = BASE_URI + '/users/' + user_id + '/playlists'
        params = dict(limit=limit, offset=offset)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    def user_albums(self, limit=None, offset=None):
        url = BASE_URI + '/me/albums'
        params = dict(limit=limit, offset=offset)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_locale_injectable('market')
    def user_tracks(self, market=None, limit=None, offset=None):
        url = BASE_URI + '/me/tracks'
        params = dict(market=market, limit=limit, offset=offset)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_locale_injectable('market')
    def playlist(self, playlist_id, market=None, fields=None):
        url = BASE_URI + '/playlists/' + playlist_id
        params = dict(market=market, fields=fields)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    def _track(self, track_id, market=None):
        url = BASE_URI + '/tracks/' + track_id
        params = dict(market=market)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_locale_injectable('market')
    def tracks(self, track_ids, market=None):
        if self._is_single_resource(track_ids):
            return self._track(track_id=self._parametrize_list(track_ids), market=market)
        url = BASE_URI + '/tracks'
        params = dict(ids=self._parametrize_list(track_ids), market=market)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    def _artist(self, artist_id):
        url = BASE_URI + '/artists/' + artist_id
        params = dict()
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    def artists(self, artist_ids):
        if self._is_single_resource(artist_ids):
            return self._artist(self._parametrize_list(artist_ids))
        url = BASE_URI + '/artists'
        params = dict(ids=self._parametrize_list(artist_ids))
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    def _album(self, album_id, market=None):
        url = BASE_URI + '/albums/' + album_id
        params = dict(market=market)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_locale_injectable('market')
    def albums(self, album_ids, market=None):
        if self._is_single_resource(album_ids):
            return self._album(self._parametrize_list(album_ids), market)
        url = BASE_URI + '/albums'
        params = dict(ids=self._parametrize_list(album_ids), market=market)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_locale_injectable('market')
    def album_tracks(self, album_id, market=None, limit=None, offset=None):
        url = BASE_URI + '/albums/' + album_id + '/tracks'
        params = dict(market=market, limit=limit, offset=offset)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_locale_injectable('market')
    def artist_albums(self, artist_id, include_groups=None, market=None, limit=None, offset=None):
        url = BASE_URI + '/artists/' + artist_id + '/albums'
        params = dict(include_groups=include_groups, market=market, limit=limit, offset=offset)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    def artist_related_artists(self, artist_id):
        url = BASE_URI + '/artists/' + artist_id + '/related-artists'
        params = {}
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_locale_injectable('country')
    def artist_top_tracks(self, artist_id, country=None):
        url = BASE_URI + '/artists/' + artist_id + '/top-tracks'
        params = dict(country=country)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    def available_genre_seeds(self):
        r = Request(method='GET', url=BASE_URI + '/recommendations/available-genre-seeds')
        return self._send_authorized_request(r).json()

    @_locale_injectable('country', support_from_token=False)
    def category(self, category_id, country=None, locale=None):
        url = BASE_URI + '/browse/categories/' + category_id
        params = dict(country=country, locale=locale)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()  

    @_locale_injectable('country', support_from_token=False)
    def categories(self, country=None, locale=None, limit=None, offset=None):
        url = BASE_URI + '/browse/categories'
        params = dict(country=country, locale=locale, limit=limit, offset=offset)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_locale_injectable('country', support_from_token=False)
    def category_playlist(self, category_id, country=None, limit=None, offset=None):
        url = BASE_URI + '/browse/categories/' + category_id + '/playlists'
        params = dict(country=country, limit=limit, offset=offset)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_locale_injectable('country', support_from_token=False)
    def featured_playlists(self, country=None, locale=None, timestamp=None, limit=None, offset=None):
        if isinstance(timestamp, datetime.datetime):
            timestamp = self._convert_to_iso_date(timestamp)
        url = BASE_URI + '/browse/featured-playlists'
        params = dict(country=country, locale=locale, timestamp=timestamp, limit=limit, offset=offset)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_locale_injectable('country', support_from_token=False)
    def new_releases(self, country=None, limit=None, offset=None):
        url = BASE_URI + '/browse/new-releases'
        params = dict(country=country, limit=limit, offset=offset)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_locale_injectable('market', support_from_token=False)
    def recommendations(
        self,
        limit=None,
        market=None,
        seed_artists=None,
        seed_genres=None,
        seed_tracks=None,
        min_acousticness=None,
        max_acousticness=None,
        target_acousticness=None,
        min_danceability=None,
        max_danceability=None,
        target_danceability=None,
        min_duration_ms=None,
        max_duration_ms=None,
        target_duration_ms=None,
        min_energy=None,
        max_energy=None,
        target_energy=None,
        min_instrumentalness=None,
        max_instrumentalness=None,
        target_instrumentalness=None,
        min_key=None,
        max_key=None,
        target_key=None,
        min_liveness=None,
        max_liveness=None,
        target_liveness=None,
        min_loudness=None,
        max_loudness=None,
        target_loudness=None,
        min_mode=None,
        max_mode=None,
        target_mode=None,
        min_popularity=None,
        max_popularity=None,
        target_popularity=None,
        min_speechiness=None,
        max_speechiness=None,
        target_speechiness=None,
        min_tempo=None,
        max_tempo=None,
        target_tempo=None,
        min_time_signature=None,
        max_time_signature=None,
        target_time_signature=None,
        min_valence=None,
        max_valence=None,
        target_valence=None
    ):
        ''' https://developer.spotify.com/documentation/web-api/reference/browse/get-recommendations/ '''
        url = BASE_URI + '/recommendations'
        params = dict(
            limit=limit,
            market=market,
            seed_artists=seed_artists,
            seed_genres=seed_genres,
            seed_tracks=seed_tracks,
            min_acousticness=min_acousticness,
            max_acousticness=max_acousticness,
            target_acousticness=target_acousticness,
            min_danceability=min_danceability,
            max_danceability=max_danceability,
            target_danceability=target_danceability,
            min_duration_ms=min_duration_ms,
            max_duration_ms=max_duration_ms,
            target_duration_ms=target_duration_ms,
            min_energy=min_energy,
            max_energy=max_energy,
            target_energy=target_energy,
            min_instrumentalness=min_instrumentalness,
            max_instrumentalness=max_instrumentalness,
            target_instrumentalness=target_instrumentalness,
            min_key=min_key,
            max_key=max_key,
            target_key=target_key,
            min_liveness=min_liveness,
            max_liveness=max_liveness,
            target_liveness=target_liveness,
            min_loudness=min_loudness,
            max_loudness=max_loudness,
            target_loudness=target_loudness,
            min_mode=min_mode,
            max_mode=max_mode,
            target_mode=target_mode,
            min_popularity=min_popularity,
            max_popularity=max_popularity,
            target_popularity=target_popularity,
            min_speechiness=min_speechiness,
            max_speechiness=max_speechiness,
            target_speechiness=target_speechiness,
            min_tempo=min_tempo,
            max_tempo=max_tempo,
            target_tempo=target_tempo,
            min_time_signature=min_time_signature,
            max_time_signature=max_time_signature,
            target_time_signature=target_time_signature,
            min_valence=min_valence,
            max_valence=max_valence,
            target_valence=target_valence
        )
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def unfollow_artists(self, artist_ids):
        url = BASE_URI + '/me/following'
        params = dict(type='artist', ids=self._parametrize_list(artist_ids))
        r = Request(method='DELETE', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def unfollow_users(self, user_ids):
        url = BASE_URI + '/me/following'
        params = dict(type='user', ids=self._parametrize_list(user_ids))
        r = Request(method='DELETE', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def unfollow_playlist(self, playlist_id):
        url = BASE_URI + '/playlists/' + playlist_id + '/followers'
        params = {}
        r = Request(method='DELETE', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def followed_artists(self, after=None, limit=None):
        url = BASE_URI + '/me/following'
        params = dict(type='artist', after=after, limit=limit)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    def follows_users(self, user_ids):
        url = BASE_URI + '/me/following/contains'
        params = dict(type='user', ids=self._parametrize_list(user_ids))
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    def follows_artists(self, artist_ids):
        url = BASE_URI + '/me/following/contains'
        params = dict(type='artist', ids=self._parametrize_list(artist_ids))
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_require_user_id(plural=True)
    def follows_playlist(self, playlist_id, user_ids=None):
        url = BASE_URI + '/playlists/' + playlist_id + '/followers/contains'
        params = dict(ids=self._parametrize_list(user_ids))
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def follow_artists(self, artist_ids):       
        url = BASE_URI + '/me/following'
        params = dict(type='artist', ids=self._parametrize_list(artist_ids))
        r = Request(method='PUT', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def follow_users(self, user_ids):       
        url = BASE_URI + '/me/following'
        params = dict(type='user', ids=self._parametrize_list(user_ids))
        r = Request(method='PUT', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json() 

    @_nullable_response
    def follow_playlist(self, playlist_id, public=None):
        url = BASE_URI + '/playlists/' + playlist_id + '/followers'
        params = {}
        data = self._json_safe_dict(dict(public=public))
        r = Request(method='PUT', url=self._safe_add_query_param(url, params), json=data)
        return self._send_authorized_request(r).json()

    @_nullable_response
    def delete_albums(self, album_ids):
        url = BASE_URI + '/me/albums'
        params = dict(ids=self._parametrize_list(album_ids))
        r = Request(method='DELETE', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def delete_tracks(self, track_ids):
        url = BASE_URI + '/me/tracks'
        params = dict(ids=self._parametrize_list(track_ids))
        r = Request(method='DELETE', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    def owns_albums(self, album_ids):
        url = BASE_URI + '/me/albums/contains'
        params = dict(ids=self._parametrize_list(album_ids))
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    def owns_tracks(self, track_ids):
        url = BASE_URI + '/me/tracks/contains'
        params = dict(ids=self._parametrize_list(track_ids))
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def save_albums(self, album_ids):
        url = BASE_URI + '/me/albums'
        params = dict(ids=self._parametrize_list(album_ids))
        r = Request(method='PUT', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def save_tracks(self, track_ids):
        url = BASE_URI + '/me/tracks'
        params = dict(ids=self._parametrize_list(track_ids))
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    def user_top_tracks(self, time_range=None, limit=None, offset=None):
        url = BASE_URI + '/me/top/tracks'
        params = dict(time_range=time_range, limit=limit, offset=offset)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    def user_top_artists(self, time_range=None, limit=None, offset=None):
        url = BASE_URI + '/me/top/artists'
        params = dict(time_range=time_range, limit=limit, offset=offset)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    def recently_played_tracks(self, limit=None, after=None, before=None):
        url = BASE_URI + '/me/player/recently-played'
        params = dict(type='track', limit=limit, after=after, before=before)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_locale_injectable('market')
    def currently_playing_info(self, market=None):
        url = BASE_URI + '/me/player'
        params = dict(market=market)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_locale_injectable('market')
    def currently_playing(self, market=None):
        url = BASE_URI + '/me/player/currently-playing'
        params = dict(market=market)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    def devices(self):
        url = BASE_URI + '/me/player/devices'
        params = dict()
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def next(self, device_id=None):
        url = BASE_URI + '/me/player/next'
        params = dict(device_id=device_id)
        r = Request(method='POST', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()
    
    @_nullable_response
    def previous(self, device_id=None):
        url = BASE_URI + '/me/player/previous'
        params = dict(device_id=device_id)
        r = Request(method='POST', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def pause(self, device_id=None):
        url = BASE_URI + '/me/player/pause'
        params = dict(device_id=device_id)
        r = Request(method='PUT', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def play(self, resource_id=None, resource_type='track', device_id=None, offset_position=None, position_ms=None):
        ''' Available types: 'track', 'artist', 'playlist', 'podcast', 'user' not sure if there's more'''
        url = BASE_URI + '/me/player/play'
        if resource_id and resource_type:
            context_uri = 'spotify:' + resource_type + ':' + resource_id
            if resource_type == 'track':
                data = self._json_safe_dict(dict(uris=list(context_uri), position_ms=position_ms))
            else:
                params = dict(device_id=device_id)
                data = self._json_safe_dict(dict(context_uri=context_uri, position_ms=position_ms))
                if offset_position:
                    offset_data = self._json_safe_dict(dict(position=offset_position))
                    if offset_data:
                        data['offset'] = offset_data
        else:
            params = dict(device_id=device_id)
            data = {}
        '''
            {
                'context_uri': context_uri, # or uris: [context_uris]
                'offset': {
                    'position': offset_position
                },
                'position_ms': position_ms
            }
        '''
        r = Request(method='PUT', url=self._safe_add_query_param(url, params), json=data)
        return self._send_authorized_request(r).json()

    @_nullable_response
    def repeat(self, state='context', device_id=None):
        url = BASE_URI + '/me/player/repeat'
        params = dict(state=state, device_id=device_id)
        r = Request(method='PUT', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def seek(self, position_ms, device_id=None):
        url = BASE_URI + '/me/player/seek'
        params = dict(position_ms=position_ms, device_id=device_id)
        r = Request(method='PUT', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def shuffle(self, state=True, device_id=None):
        url = BASE_URI + '/me/player/shuffle'
        params = dict(state=state, device_id=device_id)
        r = Request(method='PUT', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    def playback_transfer(self, device_ids):
        url = BASE_URI + '/me/player'
        params = {}
        data = self._json_safe_dict(dict(device_ids=self._parametrize_list(device_ids)))
        r = Request(method='PUT', url=self._safe_add_query_param(url, params), json=data)
        return self._send_authorized_request(r).json()

    @_nullable_response
    def volume(self, volume_percent, device_id=None):
        url = BASE_URI + '/me/player/volume'
        params = dict(volume_percent=volume_percent, device_id=device_id)
        r = Request(method='PUT', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    @_require_user_id
    def create_playlist(self, name, user_id=None, description=None, public=False, collaborative=False):
        url = BASE_URI + '/users/' + user_id + '/playlists'
        params = {}
        data = dict(name=name, description=description, public=public, collaborative=collaborative)
        r = Request(method='POST', url=self._safe_add_query_param(url, params), json=self._json_safe_dict(data))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def delete_playlist(self, playlist_id):
        ''' an alias to unfollow_playlist''' 
        return self.unfollow_playlist(playlist_id)
    
    @_locale_injectable('market')
    def playlist_tracks(self, playlist_id, market=None, fields=None, limit=None, offset=None):
        url = BASE_URI + '/playlists/' + playlist_id + '/tracks'
        params = dict(market=market, fields=fields, limit=limit, offset=offset)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def add_playlist_tracks(self, playlist_id, track_ids, position=None):
        url = BASE_URI + '/playlists/' + playlist_id + '/tracks'

        # convert IDs to uris. WHY SPOTIFY :(( ?
        if type(track_ids) == str:
            track_ids = [track_ids]
        new_list = []
        for track_id in track_ids:
            new_list.append('spotify:track:' + track_id)

        params = dict(position=position, uris=self._parametrize_list(new_list))
        r = Request(method='POST', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def delete_playlist_tracks(self, playlist_id, track_uris):
        ''' 
        track_uris supported:
        1) 'track_uri'
        2) ['track_uri', 'track_uri', 'track_uri']
        3) [
            {
                'uri': track_uri,
                'positions': [
                    position1, position2
                ]
            },
            {
                'uri': track_uri,
                'positions': position1
            },
            track_uri
        ]
        '''
        # https://developer.spotify.com/console/delete-playlist-tracks/
        url = BASE_URI + '/playlists/' + playlist_id + '/tracks'
        params = {}
        if type(track_uris) == str:
            track_uris = list(track_uris)
        if type(track_uris) == list:
            data = {
                'tracks': []
            }
            for track_uri in track_uris:
                if type(track_uri) == str:
                    data['tracks'].append(
                        {
                            'uri': 'spotify:track:' + track_uri
                        }
                    )
                elif type(track_uri) == dict:
                    positions = track_uri.get('positions')
                    if type(positions) == str or int:
                        positions = [positions]
                    data['tracks'].append(
                        {
                            'uri': 'spotify:track:' + track_uri['uri'],
                            'positions': positions
                        }
                    )
        else:
            raise TypeError('track_uris must be an instance of list or string')
        r = Request(method='DELETE', url=self._safe_add_query_param(url, params), json=data)
        return self._send_authorized_request(r).json()

    @_nullable_response
    def reorder_playlist_track(self, playlist_id, range_start=None, range_length=None, insert_before=None):
        url = BASE_URI + '/playlists/' + playlist_id + '/tracks'
        params = {}
        data = dict(range_start=range_start, range_length=range_length, insert_before=insert_before)
        r = Request(method='PUT', url=self._safe_add_query_param(url, params), json=self._json_safe_dict(data))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def update_playlist(self, playlist_id, name=None, description=None, public=None, collaborative=False):
        url = BASE_URI + '/playlists/' + playlist_id
        params = {}
        data = dict(name=name, description=description, public=public, collaborative=collaborative)
        r = Request(method='PUT', url=self._safe_add_query_param(url, params), json=self._json_safe_dict(data))
        r.headers.update(self._json_content_type_header)
        return self._send_authorized_request(r).json()

    @_locale_injectable('market')
    def search(self, q, types='track', market=None, limit=None, offset=None):
        ''' 'track' or ['track'] or 'artist' or ['track','artist'] '''
        url = BASE_URI + '/search'
        params = dict(q=q, type=self._parametrize_list(types), market=market, limit=limit, offset=offset)
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    def track_audio_analysis(self, track_id):
        url = BASE_URI + '/audio-analysis/' + track_id
        params = {}
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    def _track_audio_features(self, track_id):
        url = BASE_URI + '/audio-features/' + track_id
        params = dict()
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    def tracks_audio_features(self, track_ids):
        if self._is_single_resource(track_ids):
            return self._track_audio_features(self._parametrize_list(track_ids))
        url = BASE_URI + '/audio-features'
        params = dict(ids=self._parametrize_list(track_ids))
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    def user_profile(self, user_id):
        url = BASE_URI + '/users/' + user_id
        params = dict()
        r = Request(method='GET', url=self._safe_add_query_param(url, params))
        return self._send_authorized_request(r).json()

    @property
    def me(self):
        url = BASE_URI + '/me'
        r = Request(method='GET', url=url)
        return self._send_authorized_request(r).json()

    @property
    def is_premium(self):
        if self.me.get('type') == 'premium':
            return True
        return False
