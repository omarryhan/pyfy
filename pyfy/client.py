import json
import base64
import logging
import warnings
import datetime
from urllib import parse
from urllib3.util import Retry

from requests import Request, Session, Response
from requests.exceptions import HTTPError, Timeout, ProxyError, RetryError
from requests.adapters import HTTPAdapter
from cachecontrol import CacheControlAdapter

from .creds import (
    ClientCreds,
    UserCreds,
    ALL_SCOPES,
    _set_empty_client_creds_if_none,
    _set_empty_user_creds_if_none
)
from .excs import SpotifyError, ApiError, AuthError
from .utils import (
    _create_secret,
    _safe_get,
    _get_key_recursively,
    _locale_injectable,
    _nullable_response,
    _build_full_url,
    _safe_json_dict,
    _comma_join_list,
    _is_single_resource
)


TOKEN_EXPIRED_MSG = 'The access token expired'  # Msg sent back when token is expired
BASE_URI = 'https://api.spotify.com/v1'
OAUTH_TOKEN_URL = 'https://accounts.spotify.com/api/token'
OAUTH_AUTHORIZE_URL = 'https://accounts.spotify.com/authorize'


logger = logging.getLogger(__name__)


class Spotify:
    def __init__(self, access_token=None, client_creds=ClientCreds(), user_creds=None, ensure_user_auth=False, proxies={}, timeout=7,
                max_retries=10, enforce_state_check=True, backoff_factor=0.1, default_to_locale=True, cache=True):
        '''
        Parameters:
            client_creds: A client credentials model
            user_creds: A user credentials model
            ensure_user_auth: Whether or not to fail if user_creds provided where invalid and not refresheable
            proxies: socks or http proxies # http://docs.python-requests.org/en/master/user/advanced/#proxies & http://docs.python-requests.org/en/master/user/advanced/#socks
            timeout: Seconds before request raises a timeout error
            max_retries: Max retries before a request fails
            enforce_state_check: Check for a CSRF-token-like string. Helps verifying the identity of a callback sender thus avoiding CSRF attacks. Optional
            backoff_factor: Factor by which requests delays the next request when encountring a 429 too-many-requests error
            default_to_locale: Will pass methods decorated with @locale_injecteable the user's locale if available.
            cache: Whether or not to cache HTTP requests for the user
        '''
        # Credentials models
        self.client_creds = client_creds

        # Request defaults
        self.timeout = timeout

        # Save session attributes for when the user changes
        self.max_retries = max_retries
        self.proxies = proxies
        self.backoff_factor = backoff_factor
        self.cache = cache
        self._session = self._create_session(max_retries, proxies, backoff_factor, cache)

        # Api defaults
        self.enforce_state_check = enforce_state_check
        self.ensure_user_auth = ensure_user_auth
        self.default_to_locale = default_to_locale

        # Set User
        if access_token is not None:
            if user_creds is not None:
                raise ValueError('Either provide an access token or a user model, not both!')
            else:
                user_creds = UserCreds(access_token=access_token)
        self._user_creds = user_creds
        if self._user_creds is not None:
            # You shouldn't need to manually change this flag.from_token
            # It's bound to be equal to either the client_creds object or user_creds object depending on which was last authorized
            self._caller = self._user_creds
            if hasattr(user_creds, 'access_token') and ensure_user_auth:  # Attempt user authorization upon client instantiation
                self._check_authorization()

    def _create_session(self, max_retries, proxies, backoff_factor, cache):
        sess = Session()
        # Retry only on idempotent methods and only when too many requests
        retries = Retry(total=max_retries, backoff_factor=backoff_factor, status_forcelist=[429], method_whitelist=['GET', 'UPDATE', 'DELETE'])
        retries_adapter = HTTPAdapter(max_retries=retries)
        if cache:
            cache_adapter = CacheControlAdapter(cache_etags=True)
        sess.mount('http://', retries_adapter)
        sess.mount('http://', cache_adapter)
        sess.proxies.update(proxies)  
        return sess

    def _check_authorization(self):
        '''
        Checks whether the credentials provided are valid or not by making and api call that requires no scope but still requires authorization
        '''

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
        try:
            res = self._session.send(prepped, timeout=self.timeout)
            res.raise_for_status()
        except Timeout as e:
            raise ApiError('Request timed out.\nTry increasing the client\'s timeout period', http_response=None, http_request=r, e=e)
        except HTTPError as e:
            if res.status_code == 401:
                if res.json().get('error', None).get('message', None) == TOKEN_EXPIRED_MSG:
                    old_auth_header = r.headers['Authorization']
                    self._refresh_token()  # Should either raise an error or refresh the token
                    new_auth_header = self._access_authorization_header
                    assert new_auth_header != old_auth_header  # Assert header is changed to avoid infinite loops
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
        self._session.close()
        self._session = self._create_session(self.max_retries, self.proxies, self.backoff_factor, self.cache)
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
        '''
        Generate OAuth2 URI for authentication
        '''
        params = {
            'client_id': self.client_creds.client_id,
            'response_type': 'code',
            'redirect_uri': self.client_creds.redirect_uri,
            'scope': ' '.join(self.client_creds.scopes),
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
        '''
        Checks if user_creds or client_creds are valid (depending on who was last set)
        '''
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
    def build_user_creds(self, grant, state=None, set_user_creds=True):
        '''
        Second part of OAuth authorization code flow, Raises an AuthError if unauthorized
        Parameters:
            - grant: Code returned to user after authorizing your application
            - state: State returned from oauth callback
            - set_user_creds: Whether or not to set the user created to the client as the current active user
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

        # Set user creds
        if set_user_creds:
            self.user_creds = user_creds_model
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
                setattr(self.user_creds, key, value)

    @_set_empty_client_creds_if_none
    def _update_client_creds_with(self, client_creds_object):
        for key, value in client_creds_object.__dict__.items():
            if value is not None:
                setattr(self.client_creds, key, value)

    @staticmethod
    def _user_json_to_object(json_response):
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
        ''' utility method that can convert dates returned from Spotify's API '''
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


    ####################################################################### RESOURCES ############################################################################

##### Playback

    def devices(self):
        ''' Lists user's devices '''
        url = BASE_URI + '/me/player/devices'
        params = dict()
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def play(self, resource_id=None, resource_type='track', device_id=None, offset_position=None, position_ms=None):
        ''' Available types: 'track', 'artist', 'playlist', 'podcast', 'user' not sure if there's more'''
        url = BASE_URI + '/me/player/play'
        if resource_id and resource_type:
            context_uri = 'spotify:' + resource_type + ':' + resource_id
            if resource_type == 'track':
                data = _safe_json_dict(dict(uris=list(context_uri), position_ms=position_ms))
            else:
                params = dict(device_id=device_id)
                data = _safe_json_dict(dict(context_uri=context_uri, position_ms=position_ms))
                if offset_position:
                    offset_data = _safe_json_dict(dict(position=offset_position))
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
        r = Request(method='PUT', url=_build_full_url(url, params), json=data)
        return self._send_authorized_request(r).json()

    @_nullable_response
    def pause(self, device_id=None):
        url = BASE_URI + '/me/player/pause'
        params = dict(device_id=device_id)
        r = Request(method='PUT', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_locale_injectable('market')
    def currently_playing(self, market=None):
        url = BASE_URI + '/me/player/currently-playing'
        params = dict(market=market)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_locale_injectable('market')
    def currently_playing_info(self, market=None):
        url = BASE_URI + '/me/player'
        params = dict(market=market)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    def recently_played_tracks(self, limit=None, after=None, before=None):
        url = BASE_URI + '/me/player/recently-played'
        params = dict(type='track', limit=limit, after=after, before=before)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def next(self, device_id=None):
        url = BASE_URI + '/me/player/next'
        params = dict(device_id=device_id)
        r = Request(method='POST', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def previous(self, device_id=None):
        url = BASE_URI + '/me/player/previous'
        params = dict(device_id=device_id)
        r = Request(method='POST', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def repeat(self, state='context', device_id=None):
        url = BASE_URI + '/me/player/repeat'
        params = dict(state=state, device_id=device_id)
        r = Request(method='PUT', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def seek(self, position_ms, device_id=None):
        url = BASE_URI + '/me/player/seek'
        params = dict(position_ms=position_ms, device_id=device_id)
        r = Request(method='PUT', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def shuffle(self, state=True, device_id=None):
        url = BASE_URI + '/me/player/shuffle'
        params = dict(state=state, device_id=device_id)
        r = Request(method='PUT', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    def playback_transfer(self, device_ids):
        url = BASE_URI + '/me/player'
        params = {}
        data = _safe_json_dict(dict(device_ids=_comma_join_list(device_ids)))
        r = Request(method='PUT', url=_build_full_url(url, params), json=data)
        return self._send_authorized_request(r).json()

    @_nullable_response
    def volume(self, volume_percent, device_id=None):
        url = BASE_URI + '/me/player/volume'
        params = dict(volume_percent=volume_percent, device_id=device_id)
        r = Request(method='PUT', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

##### Playlists

    @_locale_injectable('market')
    def playlist(self, playlist_id, market=None, fields=None):
        url = BASE_URI + '/playlists/' + playlist_id
        params = dict(market=market, fields=fields)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    def user_playlists(self, user_id=None, limit=None, offset=None):
        if user_id is None:
            return self._user_playlists(limit=limit, offset=offset)
        url = BASE_URI + '/users/' + user_id + '/playlists'
        params = dict(limit=limit, offset=offset)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    def _user_playlists(self, limit=None, offset=None):
        url = BASE_URI + '/me/playlists'
        params = dict(limit=limit, offset=offset)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    def follows_playlist(self, playlist_id, user_ids=None):
        if user_ids is None:
            user_ids = self._request_user_id(user_creds=self.user_creds)
        url = BASE_URI + '/playlists/' + playlist_id + '/followers/contains'
        params = dict(ids=_comma_join_list(user_ids))
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def create_playlist(self, name, description=None, public=False, collaborative=False):
        user_id = self._request_user_id(user_creds=self.user_creds)
        url = BASE_URI + '/users/' + user_id + '/playlists'
        params = {}
        data = dict(name=name, description=description, public=public, collaborative=collaborative)
        r = Request(method='POST', url=_build_full_url(url, params), json=_safe_json_dict(data))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def follow_playlist(self, playlist_id, public=None):
        url = BASE_URI + '/playlists/' + playlist_id + '/followers'
        params = {}
        data = _safe_json_dict(dict(public=public))
        r = Request(method='PUT', url=_build_full_url(url, params), json=data)
        return self._send_authorized_request(r).json()

    @_nullable_response
    def update_playlist(self, playlist_id, name=None, description=None, public=None, collaborative=False):
        url = BASE_URI + '/playlists/' + playlist_id
        params = {}
        data = dict(name=name, description=description, public=public, collaborative=collaborative)
        r = Request(method='PUT', url=_build_full_url(url, params), json=_safe_json_dict(data))
        r.headers.update(self._json_content_type_header)
        return self._send_authorized_request(r).json()

    @_nullable_response
    def unfollow_playlist(self, playlist_id):
        url = BASE_URI + '/playlists/' + playlist_id + '/followers'
        params = {}
        r = Request(method='DELETE', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def delete_playlist(self, playlist_id):
        ''' an alias to unfollow_playlist''' 
        return self.unfollow_playlist(playlist_id)


##### Playlist Contents


    @_locale_injectable('market')
    def playlist_tracks(self, playlist_id, market=None, fields=None, limit=None, offset=None):
        url = BASE_URI + '/playlists/' + playlist_id + '/tracks'
        params = dict(market=market, fields=fields, limit=limit, offset=offset)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def add_playlist_tracks(self, playlist_id, track_ids, position=None):
        ''' track_ids can be a list of track ids or a string of one track_id'''
        url = BASE_URI + '/playlists/' + playlist_id + '/tracks'

        # convert IDs to uris. WHY SPOTIFY :(( ?
        if type(track_ids) == str:
            track_ids = [track_ids]
        new_list = []
        for track_id in track_ids:
            new_list.append('spotify:track:' + track_id)

        params = dict(position=position, uris=_comma_join_list(new_list))
        r = Request(method='POST', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def reorder_playlist_track(self, playlist_id, range_start=None, range_length=None, insert_before=None):
        url = BASE_URI + '/playlists/' + playlist_id + '/tracks'
        params = {}
        data = dict(range_start=range_start, range_length=range_length, insert_before=insert_before)
        r = Request(method='PUT', url=_build_full_url(url, params), json=_safe_json_dict(data))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def delete_playlist_tracks(self, playlist_id, track_uris):
        ''' 
        track_uris types supported:
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
        r = Request(method='DELETE', url=_build_full_url(url, params), json=data)
        return self._send_authorized_request(r).json()

##### Tracks

    @_locale_injectable('market')
    def user_tracks(self, market=None, limit=None, offset=None):
        url = BASE_URI + '/me/tracks'
        params = dict(market=market, limit=limit, offset=offset)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_locale_injectable('market')
    def tracks(self, track_ids, market=None):
        if _is_single_resource(track_ids):
            return self._track(track_id=_comma_join_list(track_ids), market=market)
        url = BASE_URI + '/tracks'
        params = dict(ids=_comma_join_list(track_ids), market=market)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    def _track(self, track_id, market=None):
        url = BASE_URI + '/tracks/' + track_id
        params = dict(market=market)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    def owns_tracks(self, track_ids):
        url = BASE_URI + '/me/tracks/contains'
        params = dict(ids=_comma_join_list(track_ids))
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def save_tracks(self, track_ids):
        url = BASE_URI + '/me/tracks'
        params = dict(ids=_comma_join_list(track_ids))
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def delete_tracks(self, track_ids):
        url = BASE_URI + '/me/tracks'
        params = dict(ids=_comma_join_list(track_ids))
        r = Request(method='DELETE', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

##### Artists

    def artists(self, artist_ids):
        if _is_single_resource(artist_ids):
            return self._artist(_comma_join_list(artist_ids))
        url = BASE_URI + '/artists'
        params = dict(ids=_comma_join_list(artist_ids))
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    def _artist(self, artist_id):
        url = BASE_URI + '/artists/' + artist_id
        params = dict()
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def followed_artists(self, after=None, limit=None):
        url = BASE_URI + '/me/following'
        params = dict(type='artist', after=after, limit=limit)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    def follows_artists(self, artist_ids):
        url = BASE_URI + '/me/following/contains'
        params = dict(type='artist', ids=_comma_join_list(artist_ids))
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def follow_artists(self, artist_ids):       
        url = BASE_URI + '/me/following'
        params = dict(type='artist', ids=_comma_join_list(artist_ids))
        r = Request(method='PUT', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def unfollow_artists(self, artist_ids):
        url = BASE_URI + '/me/following'
        params = dict(type='artist', ids=_comma_join_list(artist_ids))
        r = Request(method='DELETE', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    def artist_related_artists(self, artist_id):
        url = BASE_URI + '/artists/' + artist_id + '/related-artists'
        params = {}
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_locale_injectable('country')
    def artist_top_tracks(self, artist_id, country=None):
        url = BASE_URI + '/artists/' + artist_id + '/top-tracks'
        params = dict(country=country)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

##### Albums

    @_locale_injectable('market')
    def albums(self, album_ids, market=None):
        if _is_single_resource(album_ids):
            return self._album(_comma_join_list(album_ids), market)
        url = BASE_URI + '/albums'
        params = dict(ids=_comma_join_list(album_ids), market=market)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    def _album(self, album_id, market=None):
        url = BASE_URI + '/albums/' + album_id
        params = dict(market=market)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    def user_albums(self, limit=None, offset=None):
        url = BASE_URI + '/me/albums'
        params = dict(limit=limit, offset=offset)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    def owns_albums(self, album_ids):
        url = BASE_URI + '/me/albums/contains'
        params = dict(ids=_comma_join_list(album_ids))
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def save_albums(self, album_ids):
        url = BASE_URI + '/me/albums'
        params = dict(ids=_comma_join_list(album_ids))
        r = Request(method='PUT', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def delete_albums(self, album_ids):
        url = BASE_URI + '/me/albums'
        params = dict(ids=_comma_join_list(album_ids))
        r = Request(method='DELETE', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

##### Users

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

    def user_profile(self, user_id):
        url = BASE_URI + '/users/' + user_id
        params = dict()
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    def follows_users(self, user_ids):
        url = BASE_URI + '/me/following/contains'
        params = dict(type='user', ids=_comma_join_list(user_ids))
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def follow_users(self, user_ids):       
        url = BASE_URI + '/me/following'
        params = dict(type='user', ids=_comma_join_list(user_ids))
        r = Request(method='PUT', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json() 

    @_nullable_response
    def unfollow_users(self, user_ids):
        url = BASE_URI + '/me/following'
        params = dict(type='user', ids=_comma_join_list(user_ids))
        r = Request(method='DELETE', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

##### Others

    @_locale_injectable('market')
    def album_tracks(self, album_id, market=None, limit=None, offset=None):
        url = BASE_URI + '/albums/' + album_id + '/tracks'
        params = dict(market=market, limit=limit, offset=offset)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_locale_injectable('market')
    def artist_albums(self, artist_id, include_groups=None, market=None, limit=None, offset=None):
        url = BASE_URI + '/artists/' + artist_id + '/albums'
        params = dict(include_groups=include_groups, market=market, limit=limit, offset=offset)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    def user_top_tracks(self, time_range=None, limit=None, offset=None):
        url = BASE_URI + '/me/top/tracks'
        params = dict(time_range=time_range, limit=limit, offset=offset)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    def user_top_artists(self, time_range=None, limit=None, offset=None):
        url = BASE_URI + '/me/top/artists'
        params = dict(time_range=time_range, limit=limit, offset=offset)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_nullable_response
    def next_page(self, response=None, url=None):
        '''
        You can provide either a response dict or a url
        Providing a URL will be slightly faster as Pyfy will not have to search for the key in the response dict
        '''
        if url is None:
            url = _get_key_recursively(response, 'next', 3)
        if url is not None:
            return self._send_authorized_request(Request(method='GET', url=url)).json()
        return {}

    @_nullable_response
    def previous_page(self, response=None, url=None):
        '''
        You can provide either a response dict or a url
        Providing a URL will be slightly faster as Pyfy will not have to search for the key in the response dict
        '''
        if url is None:
            url = _get_key_recursively(response, 'previous', 3)
        if url is not None:
            return self._send_authorized_request(Request(method='GET', url=url)).json()
        return {}

##### Personalization & Explore

    @_locale_injectable('country', support_from_token=False)
    def category(self, category_id, country=None, locale=None):
        url = BASE_URI + '/browse/categories/' + category_id
        params = dict(country=country, locale=locale)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()  

    @_locale_injectable('country', support_from_token=False)
    def categories(self, country=None, locale=None, limit=None, offset=None):
        url = BASE_URI + '/browse/categories'
        params = dict(country=country, locale=locale, limit=limit, offset=offset)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_locale_injectable('country', support_from_token=False)
    def category_playlist(self, category_id, country=None, limit=None, offset=None):
        url = BASE_URI + '/browse/categories/' + category_id + '/playlists'
        params = dict(country=country, limit=limit, offset=offset)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    def available_genre_seeds(self):
        r = Request(method='GET', url=BASE_URI + '/recommendations/available-genre-seeds')
        return self._send_authorized_request(r).json()

    @_locale_injectable('country', support_from_token=False)
    def featured_playlists(self, country=None, locale=None, timestamp=None, limit=None, offset=None):
        if isinstance(timestamp, datetime.datetime):
            timestamp = self._convert_to_iso_date(timestamp)
        url = BASE_URI + '/browse/featured-playlists'
        params = dict(country=country, locale=locale, timestamp=timestamp, limit=limit, offset=offset)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_locale_injectable('country', support_from_token=False)
    def new_releases(self, country=None, limit=None, offset=None):
        url = BASE_URI + '/browse/new-releases'
        params = dict(country=country, limit=limit, offset=offset)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    @_locale_injectable('market')
    def search(self, q, types='track', market=None, limit=None, offset=None):
        ''' 'track' or ['track'] or 'artist' or ['track','artist'] '''
        url = BASE_URI + '/search'
        params = dict(q=q, type=_comma_join_list(types), market=market, limit=limit, offset=offset)
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    def track_audio_analysis(self, track_id):
        url = BASE_URI + '/audio-analysis/' + track_id
        params = {}
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    def _track_audio_features(self, track_id):
        url = BASE_URI + '/audio-features/' + track_id
        params = dict()
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()

    def tracks_audio_features(self, track_ids):
        if _is_single_resource(track_ids):
            return self._track_audio_features(_comma_join_list(track_ids))
        url = BASE_URI + '/audio-features'
        params = dict(ids=_comma_join_list(track_ids))
        r = Request(method='GET', url=_build_full_url(url, params))
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
        r = Request(method='GET', url=_build_full_url(url, params))
        return self._send_authorized_request(r).json()
