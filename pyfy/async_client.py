import json
import logging
import warnings
import datetime
from urllib import parse
import asyncio

from cachecontrol import CacheControlAdapter
from aiohttp import ClientSession, ClientTimeout, ClientRequest, ClientResponseError, ClientError
from concurrent.futures._base import TimeoutError
import backoff

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
    _prep_request,
    _resolve_async_response
)
from.base_client import (
    BaseClient,
    TOKEN_EXPIRED_MSG,
    BASE_URI,
    OAUTH_TOKEN_URL,
    OAUTH_AUTHORIZE_URL
)


logger = logging.getLogger(__name__)


class AsyncSpotify(BaseClient):
    def __init__(self, access_token=None, client_creds=ClientCreds(), user_creds=None, proxies=None, proxy_auth=None, timeout=7,
                max_retries=10, enforce_state_check=True, backoff_factor=1, default_to_locale=True, populate_user_creds=True):
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
        self.proxy_auth = proxy_auth

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
    def Session(self):
        timeout = ClientTimeout(total=self.timeout)
        return lambda: ClientSession(timeout=timeout)

    async def _send_authorized_request(self, r):
        if getattr(self._caller, 'access_is_expired', None) is True:  # True if expired and None if there's no expiry set
            await self._refresh_token()
        r['headers'].update(self._access_authorization_header)
        return await self._send_request(r)

    async def _send_request(self, r):
        # workaround to support setting instance specific timeouts and maxretries
        return await backoff.on_exception(
            wait_gen=backoff.expo,
            exception=TimeoutError,  # Not sure why this isn't working properly???
            max_tries=self.max_retries,
            max_time=self.timeout
        )(self._handle_send_request)(r)

    async def _handle_send_request(self, r):
        url = r.get('url')
        method = r.get('method')
        headers = r.get('headers')
        data = r.get('data')
        json = r.get('json')
        try:
            async with self.Session() as sess:
                logger.critical(r.__dict__)
                res = await sess.request(url=url, headers=headers, data=data, json=None, method=method, proxy=self.proxies, proxy_auth=self.proxy_auth)
            res.raise_for_status()
        except ClientResponseError as e:
            res = await _resolve_async_response(res)
            logger.critical(res.__dict__)
            if res.status_code == 401:
                if res.json.get('error', None).get('message', None) == TOKEN_EXPIRED_MSG:
                    old_auth_header = r['headers']['Authorization']
                    await self._refresh_token()  # Should either raise an error or refresh the token
                    new_auth_header = self._access_authorization_header
                    assert new_auth_header != old_auth_header  # Assert access token is changed to avoid infinite loops
                    r['headers'].update(new_auth_header)
                    return await self._send_request(r)
                else:
                    msg = res.json.get('error_description') or res.json
                    raise AuthError(msg=msg, http_response=res, http_request=r, e=e)
            elif res.status_code == 429:
                retry_after = res.headers['Retry-After']
                asyncio.sleep(retry_after)
                return await self._handle_send_request(r)
            else:
                msg = _safe_getitem(res.json, 'error', 'message') or _safe_getitem(res.json, 'error_description')
                raise ApiError(msg=msg, http_response=res, http_request=r, e=e)
        else:
            return res

    @_prep_request
    async def _check_authorization(self, **kwargs):
        '''
        Checks whether the credentials provided are valid or not by making and api call that requires no scope but still requires authorization
        '''
        try:
            await self._send_authorized_request(kwargs['r'])
        except AuthError as e:
            raise e

    async def authorize_client_creds(self, client_creds=None):
        ''' https://developer.spotify.com/documentation/general/guides/authorization-guide/ 
            Authorize with client credentials oauth flow i.e. Only with client secret and client id.
            This will give you limited functionality '''

        r = self._prep_authorize_client_creds(client_creds)
        try:
            res = await self._send_request(r)
        except ApiError as e:
            raise AuthError(msg='Failed to authenticate with client credentials', http_response=e.http_response, http_request=r, e=e)
        else:
            new_creds_json = await res.json()
            new_creds_model = self._client_json_to_object(new_creds_json)
            self._update_client_creds_with(new_creds_model)
            self._caller = self.client_creds
            await self._check_authorization()

    @property
    async def is_active(self):
        '''
        Checks if user_creds or client_creds are valid (depending on who was last set)
        '''
        if self._caller is None:
            return False
        try:
            await self._check_authorization()
        except AuthError:
            return False
        else:
            return True

    async def _refresh_token(self):
        if self._caller is self.user_creds:
            return await self._refresh_user_token()
        elif self._caller is self.client_creds:
            return await self.authorize_client_creds()
        else:
            raise AuthError('No caller to refresh token for')

    async def _refresh_user_token(self):
        r = self._prep_refresh_user_token()
        res = await self._send_request(r)
        json_res = await res.json()
        new_creds_obj = self._user_json_to_object(json_res)
        self._update_user_creds_with(new_creds_obj)

    @_set_empty_user_creds_if_none
    async def build_user_creds(self, grant, state=None, set_user_creds=True):
        '''
        Second part of OAuth authorization code flow, Raises an AuthError if unauthorized
        Parameters:
            - grant: Code returned to user after authorizing your application
            - state: State returned from oauth callback
            - set_user_creds: Whether or not to set the user created to the client as the current active user
        '''
        self._check_for_state(self, grant, state, set_user_creds)

        # Get user creds
        user_creds_json = await self._request_user_creds(grant).json()
        user_creds_model = self._user_json_to_object(user_creds_json)

        # Set user creds
        if set_user_creds:
            self.user_creds = user_creds_model
        return user_creds_model

    @_prep_request
    async def _request_user_creds(self, grant, **kwargs):
        return await self._send_request(kwargs['r'])

################################################# Resources #####################################################

    @_prep_request
    async def category(self, category_id, country=None, locale=None, **kwargs):
        res = await self._send_authorized_request(kwargs['r'])
        return await res.json()

    @_prep_request
    async def categories(self, country=None, locale=None, limit=None, offset=None, **kwargs):
        res = await self._send_authorized_request(kwargs['r'])
        return await res.json()

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
        return await self._send_authorized_request(r).json()

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
        return await self._send_authorized_request(r).json()

    @property
    async def me(self):
        res = await self._send_authorized_request(super(self.__class__, self)._prep_me())
        return await res.json()