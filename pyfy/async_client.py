from pprint import pprint, pformat
try:
    import ujson as json
except:
    import json
import logging
import asyncio
from concurrent.futures._base import TimeoutError

from aiohttp import ClientSession, ClientTimeout, ClientResponseError, TCPConnector, ClientConnectionError
import backoff

from .creds import (
    ClientCreds,
    _set_empty_user_creds_if_none
)
from .excs import ApiError, AuthError, _TooManyRequests
from .utils import (
    _safe_getitem,
)
from .wrappers import (
    _dispatch_request,
    _set_and_get_me_attr_async,
    _default_to_locale,
    _inject_user_id
)
from.base_client import (
    _BaseClient,
    TOKEN_EXPIRED_MSG,
    BASE_URI,
)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class AsyncSpotify(_BaseClient):

    IS_ASYNC = True

    def __init__(self, access_token=None, client_creds=ClientCreds(), user_creds=None, proxies=None, proxy_auth=None, timeout=7,
                max_retries=10, enforce_state_check=True, backoff_factor=0.1, default_to_locale=True, populate_user_creds=True, max_connections=1000):
        '''
        Parameters:
            client_creds: A client credentials model
            user_creds: A user credentials model
            proxies: Aiohttp proxy https://docs.aiohttp.org/en/stable/client_advanced.html#proxy-support
            proxy_auth: Aiohttp proxy auth https://docs.aiohttp.org/en/stable/client_advanced.html#proxy-support
            timeout: Seconds before request raises a timeout error
            max_retries: Max retries before a request fails
            enforce_state_check: Check for a CSRF-token-like string. Helps verifying the identity of a callback sender thus avoiding CSRF attacks. Optional
            backoff_factor: Factor by which requests delays the next request when encountring a 429 too-many-requests error
            default_to_locale: Will pass methods decorated with @_default_to_locale the user's locale if available.
            max_connections: Max TCP connections per host from the same session
            populate_user_creds: Sets user_creds info from Spotify to client's user_creds object. e.g. country. WILL OVERWRITE DATA SET TO USER CREDS IF SET TO TRUE

        '''

        # unsupported session settings
        cache = None
        ensure_user_auth = None

        self.proxy_auth = proxy_auth
        self.max_connections = max_connections

        super().__init__(access_token, client_creds, user_creds, ensure_user_auth, proxies,
            timeout, max_retries, enforce_state_check, backoff_factor, default_to_locale, cache, populate_user_creds)

    async def populate_user_creds(self):
        ''' populates self.user_creds with Spotify's info on user.
        Data is fetched from self.me() and set to user recursively '''
        me = await self.me()
        if me:
            self._populate_user_creds(me)

    def _create_session(self, cache=None, proxies=None, backoff_factor=None, max_retries=None):
        ''' Warning: Creating a client session outside of a coroutine is a very dangerous idea. See:
        https://github.com/aio-libs/aiohttp/pull/3078/commits/34b3520bc9966ee4ec41b70257960e01d86d5978 '''
        return None

    @property
    def _timeout_manager(self):
        return ClientTimeout(
            total=self.timeout
        )

    @property
    def _tcp_connector(self):
        # NOTE: limit_per_host (int) – limit for simultaneous connections to the same endpoint. Endpoints are the same if they are have equal (host, port, is_ssl) triple.
        return TCPConnector(limit_per_host=self.max_connections, enable_cleanup_closed=True)

    @property
    def _session(self):
        return ClientSession(json_serialize=json.dumps, connector=self._tcp_connector)

    async def _gather(self, *coros, return_exceptions, refresh_first):
        if refresh_first is True:
            await self._refresh_token()
        requests = [await coro for coro in coros]  # To return their request model, not an actual response
        for request in requests:
            if 'headers' not in request:
                raise TypeError('Invalid requests batch. Maybe you forgot to set "to_gather" to True?')
        responses = await self._send_authorized_requests(*requests, return_gather_exceptions=return_exceptions, gather=True)
        json_responses = [getattr(response, 'json', response) for response in responses]  # Return JSON res else response object
        return json_responses

    async def gather(self, *coros, return_exceptions=False, refresh_first=False):
        ''' 
        Use this insead of manually gathering individual requests to make all your requests that are to be gathered share one TCP connection
        
        Parameters:
            refresh_first: 
                Refresh first to avoid sending all requests at once while token isn't refreshed resulting in resending as many refresh requests.
            return_exceptions:
                passed to `asyncio.gather`: https://docs.python.org/3/library/asyncio-task.html#asyncio.gather  '''
        return await self._gather(*coros, return_exceptions=return_exceptions, refresh_first=refresh_first)

    def gather_now(self, *coros, return_exceptions=False, refresh_first=False):
        ''' 
        Use this insead of manually gathering individual requests to make all your requests that are to be gathered share one TCP connection

        same as `async def AsyncSpotify.gather` but can be called synchronously.
        Creates a new event loop if None is running

        Parameters:
            refresh_first: 
                Refresh first to avoid sending all requests at once while token isn't refreshed resulting in resending as many refresh requests
            return_exceptions:
                passed to `asyncio.gather`: https://docs.python.org/3/library/asyncio-task.html#asyncio.gather '''
        
        try:
            # Python 3.7+
            return asyncio.run(self._gather(*coros, return_exceptions=return_exceptions, refresh_first=refresh_first))
        except AttributeError:  # Python 3.6 raises: AttributeError: module 'asyncio' has no attribute 'get_running_loop'
            # Python 3.6+
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self._gather(*coros, return_exceptions=return_exceptions, refresh_first=refresh_first))

    async def _send_authorized_requests(self, *reqs, return_gather_exceptions=False, gather=False):
        if getattr(self._caller, 'access_is_expired', None) is True:  # True if expired and None if there's no expiry set
            await self._refresh_token()
        
        for req in reqs:
            req['headers'].update(self._access_authorization_header)
        return await self._send_requests(*reqs, return_gather_exceptions=return_gather_exceptions, gather=gather)


    async def _send_requests(self, *reqs, return_gather_exceptions=False, gather=False):
        async with self._session as sess:
            if gather is True:
                tasks = [asyncio.ensure_future(self._send_request_with_backoff(req, sess)) for req in reqs]
                results = await asyncio.gather(*tasks, return_exceptions=return_gather_exceptions)
            elif gather is False:
                results = await self._send_request_with_backoff(reqs[0], sess)
            else:
                await sess.close()
                raise ValueError('Gather must be either True or False')
        return results

    async def _send_request_with_backoff(self, req, sess):
        # workaround to support setting instance specific timeouts and maxretries. (Mainly because you can't pass `self` to a decorator)
        # For safety, retrying should only be performed on idempotent HTTP methods.
        # That's why I didn't include the APIError exception in the list of exceptions.
        return await backoff.on_exception(
            wait_gen=lambda: backoff.expo(factor=self.backoff_factor),
            exception=(_TooManyRequests, TimeoutError, ClientConnectionError),  # Aiohttp exception hierarchy: https://docs.aiohttp.org/en/stable/client_reference.html?highlight=exceptions#hierarchy-of-exceptions
            max_tries=self.max_retries,
            max_time=self.timeout
        )(self._handle_send_requests)(sess, req)

    async def _handle_send_requests(self, sess, r):
        logger.debug(r.url)
        res = await sess.request(
            url=r.get('url'),
            headers=r.get('headers'),
            data=r.get('data'),
            json=r.get('json'),
            method=r.get('method'),
            proxy=self.proxies,
            proxy_auth=self.proxy_auth,
            timeout=self._timeout_manager
        )
        async with res:
            res.status_code = res.status
            if res.status_code == 204:
                res.json = {}
            else:
                res.json = await res.json(content_type=None) or {}
        try:
            res.raise_for_status()
        except TimeoutError as e:
            print('\nRequest timed out, try increasing the timeout period\n')
            raise e
        except ClientResponseError as e:
            if res.status_code == 401:  # Automatically refresh and resend request
                if res.json.get('error', None).get('message', None) == TOKEN_EXPIRED_MSG:
                    old_auth_header = r['headers']['Authorization']
                    await self._refresh_token()  # Should either raise an error or refresh the token
                    new_auth_header = self._access_authorization_header
                    if new_auth_header == old_auth_header:
                        raise RuntimeError('refresh_token() was called but token wasn\'t refreshed. Execution stopped to avoid infinite looping.')
                    r['headers'].update(new_auth_header)
                    return await self._send_requests(r)
                else:
                    msg = res.json.get('error_description') or res.json  # If none, raise the whole JSON
                    raise AuthError(msg=msg, http_response=res, http_request=r, e=e)
            elif res.status_code == 429:  # Too many requests
                msg = _safe_getitem(res.json, 'error', 'message') or _safe_getitem(res.json, 'error_description')
                raise _TooManyRequests(msg=msg, http_response=res, http_request=r, e=e)
            else:
                msg = _safe_getitem(res.json, 'error', 'message') or _safe_getitem(res.json, 'error_description')
                raise ApiError(msg=msg, http_response=res, http_request=r, e=e)
        else:
            return res

    @_dispatch_request
    async def _check_authorization(self):
        '''
        Checks whether the credentials provided are valid or not by making and api call that requires no scope but still requires authorization
        '''
        return list(), dict()

    async def authorize_client_creds(self, client_creds=None):
        ''' https://developer.spotify.com/documentation/general/guides/authorization-guide/ 
            Authorize with client credentials oauth flow i.e. Only with client secret and client id.
            This will give you limited functionality '''

        r = self._prep_authorize_client_creds(client_creds)
        try:
            res = await self._send_requests(r)
        except ApiError as e:
            raise AuthError(msg='Failed to authenticate with client credentials', http_response=e.http_response, http_request=r, e=e)
        else:
            new_creds_json = res.json
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
        res = await self._send_requests(r)
        json_res = res.json
        new_creds_obj = self._user_json_to_object(json_res)
        self._update_user_creds_with(new_creds_obj)

    @_set_empty_user_creds_if_none
    async def build_user_creds(self, grant, state=None, enforce_state_check=None, set_user_creds=True):
        '''
        Second part of OAuth authorization code flow, Raises an AuthError if unauthorized
        Parameters:
            - grant: Code returned to user after authorizing your application
            - state: State returned from oauth callback
            - enforce_state_check: Check for a CSRF-token-like string. Helps verifying the identity of a callback sender thus avoiding CSRF attacks. Optional
            - set_user_creds: Whether or not to set the user created to the client as the current active user
        '''
        if enforce_state_check is not None:
            self.enforce_state_check = enforce_state_check
        self._check_for_state(grant, state, set_user_creds)

        # Get user creds
        user_creds_json = (await self._request_user_creds(grant))
        user_creds_model = self._user_json_to_object(user_creds_json)

        # Set user creds
        if set_user_creds:
            self.user_creds = user_creds_model
        return user_creds_model

    @property
    async def is_premium(self, **kwargs):
        if await _set_and_get_me_attr_async(self, 'type') == 'premium':
            return True
        return False

    @_dispatch_request(authorized_request=False)
    async def _request_user_creds(self, grant):
        return [grant], dict()

################################################# Resources #####################################################

##### Playback
    @_dispatch_request
    async def devices(self, to_gather=False):
        return [], dict(to_gather=to_gather)

    @_dispatch_request
    async def play(self, resource_id=None, resource_type='track', device_id=None, offset_position=None, position_ms=None, to_gather=False):
        ''' Available types: 'track', 'artist', 'playlist', 'podcast', 'user' not sure if there's more'''
        return [], dict(
            resource_id=resource_id,
            resource_type=resource_type,
            device_id=device_id,
            offset_position=offset_position,
            position_ms=position_ms,
            to_gather=to_gather
            )

    @_dispatch_request
    async def pause(self, device_id=None, to_gather=False):
        return [], dict(
            device_id=device_id,
            to_gather=to_gather
        )

    @_dispatch_request
    @_default_to_locale('market')
    async def currently_playing(self, market=None, to_gather=False):
        return [], dict(market=market, to_gather=to_gather)

    @_dispatch_request
    @_default_to_locale('market')
    async def currently_playing_info(self, market=None, to_gather=False):
        return [], dict(
            market=market,
            to_gather=to_gather
        )

    @_dispatch_request
    async def recently_played_tracks(self, limit=None, after=None, before=None, to_gather=False):
        return [], dict(
            limit=limit,
            after=after,
            before=before,
            to_gather=to_gather
        )

    @_dispatch_request
    async def next(self, device_id=None, to_gather=False):
        return [], dict(
            device_id=device_id,
            to_gather=to_gather
        )

    @_dispatch_request
    async def previous(self, device_id=None, to_gather=False):
        return [], dict(
            device_id=device_id,
            to_gather=to_gather
        )

    @_dispatch_request
    async def repeat(self, state='context', device_id=None, to_gather=False):
        return [], dict(
            state=state,
            device_id=device_id,
            to_gather=to_gather
        )

    @_dispatch_request
    async def seek(self, position_ms, device_id=None, to_gather=False):
        return [position_ms], dict(
            device_id=device_id,
            to_gather=to_gather
        )

    @_dispatch_request
    async def shuffle(self, state=True, device_id=None, to_gather=False):
        return [], dict(
            state=state,
            device_id=device_id,
            to_gather=to_gather
        )

    @_dispatch_request
    async def playback_transfer(self, device_ids, to_gather=False):
        return [], dict(
            device_ids=device_ids,
            to_gather=to_gather
        )

    @_dispatch_request
    async def volume(self, volume_percent, device_id=None, to_gather=False):
        return [volume_percent], dict(
            device_id=device_id,
            to_gather=to_gather
        )

##### Playlists

    @_dispatch_request
    @_default_to_locale('market')
    async def playlist(self, playlist_id, market=None, fields=None, to_gather=False):
        return [playlist_id], dict(
            market=market,
            fields=fields,
            to_gather=to_gather
        )

    @_dispatch_request
    async def user_playlists(self, user_id=None, limit=None, offset=None, to_gather=False):
        return [], dict(
            user_id=user_id,
            limit=limit,
            offset=offset,
            to_gather=to_gather
        )

    @_dispatch_request
    async def _user_playlists(self, limit=None, offset=None, to_gather=False):
        return [], dict(
            limit=limit,
            offset=offset,
            to_gather=to_gather
        )

    @_dispatch_request
    @_inject_user_id
    async def follows_playlist(self, playlist_id, user_ids=None, to_gather=False, **kwargs):
        return [playlist_id], dict(
            user_ids=user_ids,
            to_gather=to_gather,
            user_id=kwargs.get('user_id')
        )

    @_dispatch_request
    @_inject_user_id
    async def create_playlist(self, name, description=None, public=False, collaborative=False, to_gather=False, **kwargs):
        return [name], dict(
            description=description,
            public=public,
            collaborative=collaborative,
            to_gather=to_gather,
            user_id=kwargs.get('user_id')
        )

    @_dispatch_request
    async def follow_playlist(self, playlist_id, public=None, to_gather=False):
        return [playlist_id], dict(
            public=public,
            to_gather=to_gather
        )

    @_dispatch_request
    async def update_playlist(self, playlist_id, name=None, description=None, public=None, collaborative=False, to_gather=False):
        return [playlist_id], dict(
            name=name,
            description=description,
            public=public,
            collaborative=collaborative,
            to_gather=to_gather
        )

    @_dispatch_request
    async def unfollow_playlist(self, playlist_id, to_gather=False):
        return [playlist_id], dict(
            to_gather=to_gather
        )

    @_dispatch_request
    async def delete_playlist(self, playlist_id, to_gather=False):
        ''' an alias to unfollow_playlist''' 
        return [playlist_id], dict(
            to_gather=to_gather
        )


##### Playlist Contents

    @_dispatch_request
    @_default_to_locale('market')
    async def playlist_tracks(self, playlist_id, market=None, fields=None, limit=None, offset=None, to_gather=False):
        return [playlist_id], dict(
            market=market,
            fields=fields,
            limit=limit,
            offset=offset,
            to_gather=to_gather
        )

    @_dispatch_request
    async def add_playlist_tracks(self, playlist_id, track_ids, position=None, to_gather=False):
        ''' track_ids can be a list of track ids or a string of one track_id'''
        return [playlist_id, track_ids], dict(
            position=position,
            to_gather=to_gather
        )

    @_dispatch_request
    async def reorder_playlist_track(self, playlist_id, range_start=None, range_length=None, insert_before=None, to_gather=False):
        return [playlist_id], dict(
            range_start=range_start,
            range_length=range_length,
            insert_before=insert_before,
            to_gather=to_gather
        )

    @_dispatch_request
    async def delete_playlist_tracks(self, playlist_id, track_ids, to_gather=False):
        '''
        track_ids types supported:
        1) 'track_id'
        2) ['track_id', 'track_id', 'track_id']
        3) [
            {
                'id': track_id,
                'positions': [
                    position1, position2
                ]
            },
            {
                'id': track_id,
                'positions': position1
            },
            track_id
        ]
        '''
        # https://developer.spotify.com/console/delete-playlist-tracks/
        return [playlist_id, track_ids], dict(
            to_gather=to_gather
        )

##### Tracks

    @_dispatch_request
    @_default_to_locale('market')
    async def user_tracks(self, market=None, limit=None, offset=None, to_gather=False):
        return [], dict(
            market=market,
            limit=limit,
            offset=offset,
            to_gather=to_gather
        )

    @_dispatch_request
    @_default_to_locale('market')
    async def tracks(self, track_ids, market=None, to_gather=False):
        return [track_ids], dict(
            market=market,
            to_gather=to_gather
        )

    @_dispatch_request
    async def _track(self, track_id, market=None, to_gather=False):
        if to_gather is True:
            return [track_id], dict(
                market=market,
                to_gather=to_gather
            )

    @_dispatch_request
    async def owns_tracks(self, track_ids, to_gather=False):
        return [track_ids], dict(
            to_gather=to_gather
        )

    @_dispatch_request
    async def save_tracks(self, track_ids, to_gather=False):
        return [track_ids], dict(
            to_gather=to_gather
        )

    @_dispatch_request
    async def delete_tracks(self, track_ids, to_gather=False):
        return [track_ids], dict(
            to_gather=to_gather
        )

##### Artists

    @_dispatch_request
    async def artists(self, artist_ids, to_gather=False):
        return [artist_ids], dict(
            to_gather=to_gather
        )

    @_dispatch_request
    async def _artist(self, artist_id, to_gather=False):
        return [artist_id], dict(
            to_gather=to_gather
        )

    @_dispatch_request
    async def followed_artists(self, after=None, limit=None, to_gather=False):
        return [], dict(
            after=after,
            limit=limit,
            to_gather=to_gather
        )

    @_dispatch_request
    async def follows_artists(self, artist_ids, to_gather=False):
        return [artist_ids], dict(
            to_gather=to_gather
        )

    @_dispatch_request
    async def follow_artists(self, artist_ids, to_gather=False):
        return [artist_ids], dict(
            to_gather=to_gather
        )

    @_dispatch_request
    async def unfollow_artists(self, artist_ids, to_gather=False):
        return [artist_ids], dict(
            to_gather=to_gather
        )

    @_dispatch_request
    async def artist_related_artists(self, artist_id, to_gather=False):
        return [artist_id], dict(
            to_gather=to_gather
        )

    @_dispatch_request
    @_default_to_locale('country')
    async def artist_top_tracks(self, artist_id, country=None, to_gather=False):
        return [artist_id], dict(
            country=country,
            to_gather=to_gather
        )

##### Albums

    @_dispatch_request
    @_default_to_locale('market')
    async def albums(self, album_ids, market=None, to_gather=False):
        return [album_ids], dict(
            market=market,
            to_gather=to_gather
        )

    @_dispatch_request
    async def _album(self, album_id, market=None, to_gather=False):
        return [album_id], dict(
            market=market,
            to_gather=to_gather
        )

    @_dispatch_request
    async def user_albums(self, limit=None, offset=None, to_gather=False):
        return [], dict(
            limit=limit,
            offset=offset,
            to_gather=to_gather
        )

    @_dispatch_request
    async def owns_albums(self, album_ids, to_gather=False):
        return [album_ids], dict(
            to_gather=to_gather
        )

    @_dispatch_request
    async def save_albums(self, album_ids, to_gather=False):
        return [album_ids], dict(
            to_gather=to_gather
        )

    @_dispatch_request
    async def delete_albums(self, album_ids, to_gather=False):
        return [album_ids], dict(
            to_gather=to_gather
        )

##### Users

    @_dispatch_request
    async def me(self, to_gather=False):
        return [], dict(
            to_gather=to_gather
        )

    @_dispatch_request
    async def user_profile(self, user_id, to_gather=False):
        return [user_id], dict(
            to_gather=to_gather
        )

    @_dispatch_request
    async def follows_users(self, user_ids, to_gather=False):
        return [user_ids], dict(
            to_gather=to_gather
        )

    @_dispatch_request
    async def follow_users(self, user_ids, to_gather=False):
        return [user_ids], dict(
            to_gather=to_gather
        )

    @_dispatch_request
    async def unfollow_users(self, user_ids, to_gather=False):
        return [user_ids], dict(
            to_gather=to_gather
        )


##### Others

    @_dispatch_request
    @_default_to_locale('market')
    async def album_tracks(self, album_id, market=None, limit=None, offset=None, to_gather=False):
        return [album_id], dict(
            market=market,
            limit=limit,
            offset=offset,
            to_gather=to_gather
        )

    @_dispatch_request
    @_default_to_locale('market')
    async def artist_albums(self, artist_id, include_groups=None, market=None, limit=None, offset=None, to_gather=False):
        return [artist_id], dict(
            include_groups=include_groups,
            market=market,
            limit=limit,
            offset=offset,
            to_gather=to_gather
        )

    @_dispatch_request
    async def user_top_tracks(self, time_range=None, limit=None, offset=None, to_gather=False):
        return [], dict(
            time_range=time_range,
            limit=limit,
            offset=offset,
            to_gather=to_gather
        )

    @_dispatch_request
    async def user_top_artists(self, time_range=None, limit=None, offset=None, to_gather=False):
        return [], dict(
            time_range=time_range,
            limit=limit,
            offset=offset,
            to_gather=to_gather
        )

    @_dispatch_request
    async def next_page(self, response=None, url=None, to_gather=False):
        '''
        You can provide either a response dict or a url
        Providing a URL will be slightly faster as Pyfy will not have to search for the key in the response dict
        '''
        return [], dict(
            response=response,
            url=url,
            to_gather=to_gather
        )

    @_dispatch_request
    async def previous_page(self, response=None, url=None, to_gather=False):
        '''
        You can provide either a response dict or a url
        Providing a URL will be slightly faster as Pyfy will not have to search for the key in the response dict
        '''
        return [], dict(
            response=response,
            url=url,
            to_gather=to_gather
        )


##### Personalization & Explore

    @_dispatch_request
    @_default_to_locale('country', support_from_token=False)
    async def category(self, category_id, country=None, locale=None, to_gather=False):
        return [category_id], dict(
            country=country,
            locale=locale,
            to_gather=to_gather
        )

    @_dispatch_request
    @_default_to_locale('country', support_from_token=False)
    async def categories(self, country=None, locale=None, limit=None, offset=None, to_gather=False):
        return [], dict(
            country=country,
            locale=locale,
            limit=limit,
            offset=offset,
            to_gather=to_gather
        )

    @_dispatch_request
    @_default_to_locale('country', support_from_token=False)
    async def category_playlist(self, category_id, country=None, limit=None, offset=None, to_gather=False):
        return [category_id], dict(
            country=country,
            limit=limit,
            offset=offset,
            to_gather=to_gather
        )

    @_dispatch_request
    async def available_genre_seeds(self, to_gather=False):
        return [], dict(
            to_gather=to_gather
        )

    @_dispatch_request
    @_default_to_locale('country', support_from_token=False)
    async def featured_playlists(self, country=None, locale=None, timestamp=None, limit=None, offset=None, to_gather=False):
        return [], dict(
            country=country,
            locale=locale,
            timestamp=timestamp,
            limit=limit,
            offset=offset,
            to_gather=to_gather
        )

    @_dispatch_request
    @_default_to_locale('country', support_from_token=False)
    async def new_releases(self, country=None, limit=None, offset=None, to_gather=False):
        return [], dict(
            country=country,
            limit=limit,
            offset=offset,
            to_gather=to_gather
        )

    @_dispatch_request
    @_default_to_locale('market')
    async def search(self, q, types='track', market=None, limit=None, offset=None, to_gather=False):
        ''' 'track' or ['track'] or 'artist' or ['track','artist'] '''
        return [q], dict(
            types=types,
            market=market,
            limit=limit,
            offset=offset,
            to_gather=to_gather
        )

    @_dispatch_request
    async def track_audio_analysis(self, track_id, to_gather=False):
        return [track_id], dict(
            to_gather=to_gather
        )

    @_dispatch_request
    async def tracks_audio_features(self, track_ids, to_gather=False):
        return [track_ids], dict(
            to_gather=to_gather
        )

    @_dispatch_request
    @_default_to_locale('market', support_from_token=False)
    async def recommendations(
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
        target_valence=None,
        to_gather=False
    ):
        ''' https://developer.spotify.com/documentation/web-api/reference/browse/get-recommendations/ '''
        return [], dict(
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
            target_valence=target_valence,
            to_gather=to_gather
        )
