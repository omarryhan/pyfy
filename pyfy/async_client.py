import json
import logging
import warnings
import datetime
from urllib import parse
from urllib3.util import Retry

from requests import Request, Session, Response
from requests.exceptions import HTTPError, Timeout
from requests.adapters import HTTPAdapter
from cachecontrol import CacheControlAdapter
from aiohttp import ClientSession, ClientTimeout, ClientRequest

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
    _safe_getitem,
    _get_key_recursively,
    _locale_injectable,
    _nullable_response,
    _build_full_url,
    _safe_json_dict,
    _comma_join_list,
    _is_single_resource,
    _convert_to_iso_date,
    convert_from_iso_date,
    _prep_request
)
from.base_client import (
    BaseClient,
    TOKEN_EXPIRED_MSG,
    BASE_URI,
    OAUTH_TOKEN_URL,
    OAUTH_AUTHORIZE_URL
)


class AsyncSpotify(BaseClient):
    def __init__(self, access_token=None, client_creds=ClientCreds(), user_creds=None, proxies=None, timeout=60*5,
                max_retries=10, enforce_state_check=True, backoff_factor=0.1, default_to_locale=True, populate_user_creds=True):
        '''
        Parameters:
            client_creds: A client credentials model
            user_creds: A user credentials model
            proxies: Aiohttp proxy https://docs.aiohttp.org/en/stable/client_advanced.html#proxy-support
            timeout: Seconds before request raises a timeout error
            max_retries: Max retries before a request fails
            enforce_state_check: Check for a CSRF-token-like string. Helps verifying the identity of a callback sender thus avoiding CSRF attacks. Optional
            backoff_factor: Factor by which requests delays the next request when encountring a 429 too-many-requests error
            default_to_locale: Will pass methods decorated with @locale_injecteable the user's locale if available.
                IMPORTANT: Must first await populate_user_creds in order to successfully default to locale
        '''

        # unsupported session settings
        cache = None
        ensure_user_auth = None

        self._is_async = True

        super().__init__(access_token, client_creds, user_creds, ensure_user_auth, proxies,
            timeout, max_retries, enforce_state_check, backoff_factor, default_to_locale, cache, populate_user_creds)

    async def populate_user_creds(self):
        me = await self.me
        if me:
            self._populate_user_creds(me)


    def _create_session(self, cache=None, proxies=None, backoff_factor=None, max_retries=None):
        ''' Warning: Creating a client session outside of a coroutine is a very dangerous idea. See:
        https://github.com/aio-libs/aiohttp/pull/3078/commits/34b3520bc9966ee4ec41b70257960e01d86d5978 '''
        return None

    @property
    def _session(self):
        timeout = ClientTimeout(total=self.timeout)
        return lambda: ClientSession(timeout=timeout)

    async def _send_authorized_request(self):
        pass

    async def _send_request(self):
        pass

    async def _check_authorization(self):
        pass

    async def _authorize_client_creds(self):
        pass

    async def _is_active(self):
        pass

    async def _refresh_token(self):
        pass

    async def _refresh_user_token(self):
        pass

    @_set_empty_user_creds_if_none
    async def build_user_creds(self, grant, state=None, set_user_creds=True):
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

    async def _request_user_creds(self, grant):
        data = {
            'grant_type': 'authorization_code',
            'code': grant,
            'redirect_uri': self.client_creds.redirect_uri
        }
        headers = {**self._client_authorization_header, **self._form_url_encoded_type_header}
        return self._send_request(Request(method='POST', url=OAUTH_TOKEN_URL, headers=headers, data=data))

    # Rewrite those
    async def follows_playlist(self, playlist_id, user_ids=None, **kwargs):
        if user_ids is None:
            if getattr(self.user_creds, 'id', None) is None:
                if self._populate_user_creds_:
                    await self.populate_user_creds()
                    user_ids = getattr(self.user_creds, 'id')
                else:
                    user_ids = await self.me.get('id')
            else:
                user_ids = self.user_creds.id  
        r =  self._prep_follows_playlist(playlist_id, user_ids)
        return self._send_authorized_request(r).json()

    # Rewrite those
    @_nullable_response
    async def create_playlist(self, name, description=None, public=False, collaborative=False, **kwargs):
        if getattr(self.user_creds, 'id', None) is None:
            if self._populate_user_creds_:
                await self.populate_user_creds()
                user_id = getattr(self.user_creds, 'id')
            else:
                user_id = await self.me.get('id')
        else:
            user_id = self.user_creds.id  
        r = self._prep_create_playlist(name, user_id, description, public, collaborative)
        return self._send_authorized_request(r).json()
