from pprint import pprint, pformat
import warnings

try:
    import ujson as json
except:
    import json
import logging
import asyncio
from concurrent.futures._base import TimeoutError

from aiohttp import (
    ClientSession,
    ClientTimeout,
    ClientResponseError,
    TCPConnector,
    ClientConnectionError,
)
import backoff

from .creds import ClientCreds, _set_empty_user_creds_if_none
from .excs import ApiError, AuthError, _TooManyRequests
from .utils import _safe_getitem
from .wrappers import (
    _dispatch_request,
    _set_and_get_me_attr_async,
    _default_to_locale,
    _inject_user_id,
)
from .base_client import _BaseClient, TOKEN_EXPIRED_MSG, BASE_URI


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class AsyncSpotify(_BaseClient):
    """
    Spotify's Asynchronous Client

    Arguments:
        
        client_creds (pyfy.creds.ClientCreds): A client credentials model
        
        user_creds (pyfy.creds.UserCreds): A user credentials model
        
        ensure_user_auth (bool):
        
            * Whether or not to fail upon instantiation if user_creds provided where invalid and not refresheable.
            
            * Default: False
    
        proxies: Aiohttp proxy https://docs.aiohttp.org/en/stable/client_advanced.html#proxy-support
        
        proxy_auth: Aiohttp proxy auth https://docs.aiohttp.org/en/stable/client_advanced.html#proxy-support
        
        timeout (int):
        
            * Seconds before request raises a timeout error

            * Default: 7
        
        max_retries (int):
        
            * Max retries before a request fails

            * Default: 10
        
        backoff_factor (float):
        
            * Factor by which requests delays the next request when encountring a 429 too-many-requests error

            * Default: 0.1
        
        default_to_locale (bool):
        
            * Will pass methods decorated with @_default_to_locale the user's locale if available.

            * Default: True
        
        populate_user_creds (bool):
        
            * Sets user_creds info from Spotify to client's user_creds object. e.g. country.

            * Default: True
        
        max_connections (int):
        
            * Max TCP connections per host from the same session

            * Default: 1000
    """

    IS_ASYNC = True

    def __init__(
        self,
        access_token=None,
        client_creds=ClientCreds(),
        user_creds=None,
        proxies=None,
        proxy_auth=None,
        timeout=7,
        max_retries=10,
        enforce_state_check=None,
        backoff_factor=0.1,
        default_to_locale=True,
        populate_user_creds=True,
        max_connections=1000,
    ):

        # unsupported session settings
        cache = None
        ensure_user_auth = None

        self.proxy_auth = proxy_auth
        self.max_connections = max_connections

        super().__init__(
            access_token,
            client_creds,
            user_creds,
            ensure_user_auth,
            proxies,
            timeout,
            max_retries,
            enforce_state_check,
            backoff_factor,
            default_to_locale,
            cache,
            populate_user_creds,
        )

    async def populate_user_creds(self):
        """ 
        Populates self.user_creds with Spotify's info on user.
        Data is fetched from self.me() and set to user recursively
        """
        me = await self.me()
        if me:
            self._populate_user_creds(me)

    def _create_session(
        self, cache=None, proxies=None, backoff_factor=None, max_retries=None
    ):
        """ Warning: Creating a client session outside of a coroutine is a very dangerous idea. See:
        https://github.com/aio-libs/aiohttp/pull/3078/commits/34b3520bc9966ee4ec41b70257960e01d86d5978 """
        return None

    @property
    def _timeout_manager(self):
        return ClientTimeout(total=self.timeout)

    @property
    def _tcp_connector(self):
        # NOTE: limit_per_host (int) – limit for simultaneous connections to the same endpoint. Endpoints are the same if they are have equal (host, port, is_ssl) triple.
        return TCPConnector(
            limit_per_host=self.max_connections, enable_cleanup_closed=True
        )

    @property
    def _session(self):
        return ClientSession(json_serialize=json.dumps, connector=self._tcp_connector)

    async def _gather(self, *coros, return_exceptions, refresh_first):
        if refresh_first is True:
            await self._refresh_token()
        requests = [
            await coro for coro in coros
        ]  # To return their request model, not an actual response
        for request in requests:
            if "headers" not in request:
                raise TypeError(
                    'Invalid requests batch. Maybe you forgot to set "to_gather" to True?'
                )
        responses = await self._send_authorized_requests(
            *requests, return_gather_exceptions=return_exceptions, gather=True
        )
        json_responses = [
            getattr(response, "json", response) for response in responses
        ]  # Return JSON res else response object
        return json_responses

    async def gather(self, *coros, return_exceptions=False, refresh_first=False):
        """ 
        Use this insead of manually gathering individual requests to make all your requests that are to be gathered share one TCP connection
        
        Note:

            It is recommended that you leave return_exceptions as False, as setting it to true will return exceptions as str instead of raising them.
            Having exceptions fly by isn't a really a great idea.

        Arguments:

            refresh_first (bool): 
                Refresh first to avoid sending all requests at once while token isn't refreshed resulting in resending as many refresh requests.
            
            return_exceptions (bool):
                passed to `asyncio.gather`: https://docs.python.org/3/library/asyncio-task.html#asyncio.gather  
                
        """
        return await self._gather(
            *coros, return_exceptions=return_exceptions, refresh_first=refresh_first
        )

    def gather_now(self, *coros, return_exceptions=False, refresh_first=False):
        """ 
        Use this insead of manually gathering individual requests to make all your requests that are to be gathered share one TCP connection

        same as ``async def AsyncSpotify.gather`` but can be called synchronously.
        Only works if there's no loop running. Use the ``gather`` method if you have one already running.

        Note:

            It is recommended that you leave return_exceptions as False, as setting it to true will return exceptions as str instead of raising them.
            Having exceptions fly by isn't a really a great idea.

        Arguments:

            refresh_first (bool): 
                Refresh first to avoid sending all requests at once while token isn't refreshed resulting in resending as many refresh requests.
            
            return_exceptions (bool):
                passed to `asyncio.gather`: https://docs.python.org/3/library/asyncio-task.html#asyncio.gather  
                
        """

        try:
            # Python 3.7+
            return asyncio.run(
                self._gather(
                    *coros,
                    return_exceptions=return_exceptions,
                    refresh_first=refresh_first
                )
            )
        except AttributeError:  # Python 3.6 raises: AttributeError: module 'asyncio' has no attribute 'get_running_loop'
            # Python 3.6+
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(
                self._gather(
                    *coros,
                    return_exceptions=return_exceptions,
                    refresh_first=refresh_first
                )
            )

    async def _send_authorized_requests(
        self, *reqs, return_gather_exceptions=False, gather=False
    ):
        if (
            getattr(self._caller, "access_is_expired", None) is True
        ):  # True if expired and None if there's no expiry set
            await self._refresh_token()

        for req in reqs:
            req["headers"].update(self._access_authorization_header)
        return await self._send_requests(
            *reqs, return_gather_exceptions=return_gather_exceptions, gather=gather
        )

    async def _send_requests(self, *reqs, return_gather_exceptions=False, gather=False):
        async with self._session as sess:
            if gather is True:
                tasks = [
                    asyncio.ensure_future(self._send_request_with_backoff(req, sess))
                    for req in reqs
                ]
                results = await asyncio.gather(
                    *tasks, return_exceptions=return_gather_exceptions
                )
            elif gather is False:
                results = await self._send_request_with_backoff(reqs[0], sess)
            else:
                await sess.close()
                raise ValueError("Gather must be either True or False")
        return results

    async def _send_request_with_backoff(self, req, sess):
        # workaround to support setting instance specific timeouts and maxretries. (Mainly because you can't pass `self` to a decorator)
        # For safety, retrying should only be performed on idempotent HTTP methods.
        # That's why I didn't include the APIError exception in the list of exceptions.
        return await backoff.on_exception(
            wait_gen=lambda: backoff.expo(factor=self.backoff_factor),
            exception=(
                _TooManyRequests,
                TimeoutError,
                ClientConnectionError,
            ),  # Aiohttp exception hierarchy: https://docs.aiohttp.org/en/stable/client_reference.html?highlight=exceptions#hierarchy-of-exceptions
            max_tries=self.max_retries,
            max_time=self.timeout,
        )(self._handle_send_requests)(sess, req)

    async def _handle_send_requests(self, sess, r):
        logger.debug(r.url)
        res = await sess.request(
            url=r.get("url"),
            headers=r.get("headers"),
            data=r.get("data"),
            json=r.get("json"),
            method=r.get("method"),
            proxy=self.proxies,
            proxy_auth=self.proxy_auth,
            timeout=self._timeout_manager,
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
            logger.error("\nRequest timed out, try increasing the timeout period\n")
            raise e
        except ClientResponseError as e:
            if res.status_code == 401:  # Automatically refresh and resend request
                if (
                    res.json.get("error", None).get("message", None)
                    == TOKEN_EXPIRED_MSG
                ):
                    old_auth_header = r["headers"]["Authorization"]
                    await self._refresh_token()  # Should either raise an error or refresh the token
                    new_auth_header = self._access_authorization_header
                    if new_auth_header == old_auth_header:
                        msg = "refresh_token() was successfully called but token wasn't refreshed. Execution stopped to avoid infinite looping."
                        logger.critical(msg)
                        raise RuntimeError(msg)
                    r["headers"].update(new_auth_header)
                    return await self._send_requests(r)
                else:
                    msg = (
                        res.json.get("error_description") or res.json
                    )  # If none, raise the whole JSON
                    raise AuthError(msg=msg, http_response=res, http_request=r, e=e)
            elif res.status_code == 429:  # Too many requests
                msg = _safe_getitem(res.json, "error", "message") or _safe_getitem(
                    res.json, "error_description"
                )
                raise _TooManyRequests(msg=msg, http_response=res, http_request=r, e=e)
            else:
                msg = _safe_getitem(res.json, "error", "message") or _safe_getitem(
                    res.json, "error_description"
                )
                raise ApiError(msg=msg, http_response=res, http_request=r, e=e)
        else:
            return res

    @_dispatch_request
    async def _check_authorization(self):
        """
        Checks whether the credentials provided are valid or not by making and api call that requires no scope but still requires authorization
        """
        return list(), dict()

    async def authorize_client_creds(self, client_creds=None):
        """ 
        Authorize with client credentials oauth flow i.e. Only with client secret and client id.

        Call this to send request using client credentials.
        
        https://developer.spotify.com/documentation/general/guides/authorization-guide/ 
        
        Note:

            This will give you limited access to most endpoints

        Arguments:

            client_creds (pyfy.creds.ClientCreds): Client Credentials object. Defaults to ``self.client_creds``

        Raises:

            pyfy.excs.AuthErrror: 
        """

        r = self._prep_authorize_client_creds(client_creds)
        try:
            res = await self._send_requests(r)
        except ApiError as e:
            raise AuthError(
                msg="Failed to authenticate with client credentials",
                http_response=e.http_response,
                http_request=r,
                e=e,
            )
        else:
            new_creds_json = res.json
            new_creds_model = self._client_json_to_object(new_creds_json)
            self._update_client_creds_with(new_creds_model)
            self._caller = self.client_creds
            await self._check_authorization()

    @property
    async def is_active(self):
        """
        Checks if user_creds or client_creds are valid (depending on who was last set)
        """
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
            raise AuthError("No caller to refresh token for")

    async def _refresh_user_token(self):
        r = self._prep_refresh_user_token()
        res = await self._send_requests(r)
        json_res = res.json
        new_creds_obj = self._user_json_to_object(json_res)
        self._update_user_creds_with(new_creds_obj)

    @_set_empty_user_creds_if_none
    async def build_user_creds(
        self, grant, state=None, enforce_state_check=None, set_user_creds=True
    ):
        """
        Second part of OAuth2 authorization code flow, Raises an AuthError if unauthorized

        Arguments:

            grant (str): Code returned to user after authorizing your application
            
            set_user_creds (bool): Whether or not to set the user created to the client as the current active user

        Returns:

            pyfy.creds.UserCreds: User Credentials Model
        """
        if state is not None or enforce_state_check is not None:
            warning_msg = """
            state and enforce_state_check are deprecated and will be removed soon. 
            Please remove those arguments and manually validate them instead
            """
            warnings.warn(warning_msg, DeprecationWarning)
            check = enforce_state_check or self.enforce_state_check
            if check is True:
                if state != self.user_creds.state:
                    raise AuthError("Invalid state")

        # Get user creds
        user_creds_json = await self._request_user_creds(grant)
        user_creds_model = self._user_json_to_object(user_creds_json)

        # Set user creds
        if set_user_creds:
            self.user_creds = user_creds_model
        return user_creds_model

    @property
    async def is_premium(self, **kwargs):
        """
        Checks whether user is premium or not

        Returns:

            bool:
        """
        if await _set_and_get_me_attr_async(self, "product") == "premium":
            return True
        return False

    @_dispatch_request(authorized_request=False)
    async def _request_user_creds(self, grant):
        return [grant], dict()

    ################################################# Resources #####################################################

    ##### Playback
    @_dispatch_request
    async def devices(self, *args, **kwargs):
        """
        Lists user's devices

        Arguments:

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def play(self, *args, **kwargs):
        """
        Starts playback

        Note:
        
            Available resource types:
            
            - 'track'
            
            - 'artist'
            
            - 'playlist'
            
            - 'podcast'
            
            - 'user' 
            
            * There might be more
        
        Arguments:

            resource_id (str): 
            
                * Optional

                * ID of the resource

            resource_type (str):
            
                * Optional

                * Type of the resource.

            device_id (str):

                * Optional

            offset_position (int): 

                * Optional

            poition_ms (int):

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def pause(self, *args, **kwargs):
        """
        Pauses playback

        Arguments:

            device_id (str):

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("market")
    async def currently_playing(self, *args, **kwargs):
        """
        Lists currenly playing

        Arguments:

            market (str):

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("market")
    async def currently_playing_info(self, *args, **kwargs):
        """
        Lists currently playing info

        Arguments:

            market (str):

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def recently_played_tracks(self, *args, **kwargs):
        """
        Lists recently played tracks

        Arguments:

            limit (int):

                * Optional

            after:

                * Optional

            before:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def next(self, *args, **kwargs):
        """
        Next playback

        Arguments:

            device_id:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def previous(self, *args, **kwargs):
        """
        Previous Playback

        Arguments:

            device_id:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def repeat(self, *args, **kwargs):
        """
        Toggle repeat

        Arguments:

            state:

                * Optional

                * Default: 'context'

            device_id:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def seek(self, *args, **kwargs):
        """
        Seek Playback

        Arguments:

            posiotion_ms:

                * Required

            device_id:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def shuffle(self, *args, **kwargs):
        """
        Shuffle Playback

        Arguments:

            state:

                * Optional

                * Default: True

            device_id:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def playback_transfer(self, *args, **kwargs):
        """
        Transfer playback to another device

        Arguments:

            device_ids (list, str):

                * Required

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def volume(self, *args, **kwargs):
        """
        Change volume

        Arguments:

            volume_percent (int):

                * Required

            device_id:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    ##### Playlists

    @_dispatch_request
    @_default_to_locale("market")
    async def playlist(self, *args, **kwargs):
        """
        Lists playlist

        Arguments:

            playlist_id:

                * Required

            market:

                * Optional

            fields:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def user_playlists(self, *args, **kwargs):
        """
        Lists playlists owned by a user

        Arguments:

            user_id:

                * Optional

                * Defaults to user's

            limit:

                * Optional

            offset:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_inject_user_id
    async def follows_playlist(self, *args, **kwargs):
        """
        Lists whether or not user follows a playlist

        Arguments:

            playlist_id:

                * Required

            user_ids (list, str):

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_inject_user_id
    async def create_playlist(self, *args, **kwargs):
        """
        Creates a playlist

        Arguments:

            name:

                * Required

            description:

                * Optional

            public:

                * Optional
                
                * Default: False

            collaborative:

                * Optional

                * default: False

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def follow_playlist(self, *args, **kwargs):
        """
        Follows a playlist

        Arguments:

            playlist_id:

                * Required

            public:

                * Optional

                * Default: False

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def update_playlist(self, *args, **kwargs):
        """
        Updates a playlist

        Arguments:

            playlist_id:

                * Required

            name:

                * Optional

            description:

                * Optional

            public:

                * Optional

            collaborative:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def unfollow_playlist(self, *args, **kwargs):
        """
        Unfollow a playlist

        Arguments:

            playlist_id:

                * Required

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def delete_playlist(self, *args, **kwargs):
        """
        An alias to unfollow_playlist

        Arguments:

            playlist_id:

                * Required

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    ##### Playlist Contents

    @_dispatch_request
    @_default_to_locale("market")
    async def playlist_tracks(self, *args, **kwargs):
        """
        List tracks in a playlist

        Arguments:

            playlist_id:

                * Required

            market:

                * Optional

            fields:

                * Optional

            limit:

                * Optional

            offset:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def add_playlist_tracks(self, *args, **kwargs):
        """
        Add tracks to a playlist

        Arguments:

            playlist_id:

                * Required

            track_ids (str, list):

                * Required

            position:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def reorder_playlist_track(self, *args, **kwargs):
        """
        Reorder tracks in a playlist

        Arguments:

            playlist_id:

                * Required

            range_start:

                * Optional

            range_length:

                * Optional

            insert_before:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def delete_playlist_tracks(self, *args, **kwargs):
        """
        Delete tracks from a playlist
        
        https://developer.spotify.com/console/delete-playlist-tracks/


        Examples:

            ``track_ids`` types supported: ::
                
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

        Arguments:

            playlist_id:

                * Required

            track_ids:

                * Required

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    ##### Tracks

    @_dispatch_request
    @_default_to_locale("market")
    async def user_tracks(self, *args, **kwargs):
        """
        List user's tracks

        Arguments:

            market:

                * Optional

            limit:

                * Optional

            offset:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("market")
    async def tracks(self, *args, **kwargs):
        """
        List tracks

        Arguments:

            track_ids (str, list):

                * Required

            market:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def owns_tracks(self, *args, **kwargs):
        """
        Lists whether or not current user owns tracks

        Arguments:

            track_ids (str, list):

                * Required

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def save_tracks(self, *args, **kwargs):
        """
        Save tracks

        Arguments:

            track_ids (str, list):

                * Required

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def delete_tracks(self, *args, **kwargs):
        """
        Delete user's tracks

        Arguments:

            track_ids (str, list):


            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:
                * Required
        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    ##### Artists

    @_dispatch_request
    async def artists(self, *args, **kwargs):
        """
        List artists

        Arguments:

            artist_ids (str, list):


            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:
                * Required
        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def followed_artists(self, *args, **kwargs):
        """
        List artists followed by current user

        Arguments:

            after:

                * Optional

            limit:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def follows_artists(self, *args, **kwargs):
        """
        Whether or not current user follows an artist(s)

        Arguments:

            artist_ids (str, list):

                * Required

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def follow_artists(self, *args, **kwargs):
        """
        Follow an artist(s)

        Arguments:

            artist_ids (str, list):

                * Required

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def unfollow_artists(self, *args, **kwargs):
        """
        Unfollow artist(s)

        Arguments:

            artist_ids (str, list):

                * Required

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def artist_related_artists(self, *args, **kwargs):
        """
        List artists related to an artist

        Arguments:

            artist_id (str):

                * Required

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("country")
    async def artist_top_tracks(self, *args, **kwargs):
        """
        List top tracks of an artist

        Arguments:

            artist_id (str):

                * Required

            country:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    ##### Albums

    @_dispatch_request
    @_default_to_locale("market")
    async def albums(self, *args, **kwargs):
        """
        List Albums

        Arguments:

            album_ids (str, list):

                * Required

            market:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def user_albums(self, *args, **kwargs):
        """
        Albums owned by current user

        Arguments:

            limit:

                * Optional

            offset:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def owns_albums(self, *args, **kwargs):
        """
        Whether or not current user owns an album(s)

        Arguments:

            album_ids (str, list):

                * Required

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def save_albums(self, *args, **kwargs):
        """
        Save Albums

        Arguments:

            album_ids (str, list):

                * Required

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def delete_albums(self, *args, **kwargs):
        """
        Delete Albums

        Arguments:

            album_ids (str, list):

                * Required

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    ##### Users

    @_dispatch_request
    async def me(self, *args, **kwargs):
        """
        List current user's profile

        Arguments:

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def user_profile(self, *args, **kwargs):
        """
        List a user's profile

        Arguments:

            user_id (str):

                * Required

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def follows_users(self, *args, **kwargs):
        """
        Whether or not current user follows a user(s)

        Arguments:

            user_ids (str, list):

                * Required

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def follow_users(self, *args, **kwargs):
        """
        Follow a user

        Arguments:

            user_ids (str, list):

                * Required

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def unfollow_users(self, *args, **kwargs):
        """
        Unfollow user(s)

        Arguments:

            user_ids (str, list):

                * Required

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    ##### Others

    @_dispatch_request
    @_default_to_locale("market")
    async def album_tracks(self, *args, **kwargs):
        """
        List tracks of an album

        Arguments:

            album_id (str):

                * Required

            market:

                * Optional

            limit:

                * Optional

            offset:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("market")
    async def artist_albums(self, *args, **kwargs):
        """
        List albums of an artist

        Arguments:

            artist_id (str):

                * Required

            include_groups:

                * Optional

            market:

                * Optional

            limit:

                * Optional

            offset:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def user_top_tracks(self, *args, **kwargs):
        """
        List top tracks of a user

        Arguments:

            time_range:

                * Optional

            limit:

                * Optional

            offset:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def user_top_artists(self, *args, **kwargs):
        """
        List top artists of a user

        Arguments:

            time_range:

                * Optional

            limit:

                * Optional

            offset:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def next_page(self, *args, **kwargs):
        """
        Next Page

        Note:

            * You can either provide a response or a url
            
            * Providing a URL will be slightly faster as Pyfy will not have to search for the key in the response dict

        Arguments:

            response (dict):

                * Optional

            url (str):

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def previous_page(self, *args, **kwargs):
        """
        Previous Page

        Note:

            * You can either provide a response or a url
            
            * Providing a URL will be slightly faster as Pyfy will not have to search for the key in the response dict

        Arguments:

            response (dict):

                * Optional

            url (str):

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    ##### Personalization & Explore

    @_dispatch_request
    @_default_to_locale("country", support_from_token=False)
    async def category(self, *args, **kwargs):
        """
        List Category

        Arguments:

            category_id:

                * Required

            country:

                * Optional

            locale:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("country", support_from_token=False)
    async def categories(self, *args, **kwargs):
        """
        List Categories

        Arguments:

            country:

                * Optional

            locale:

                * Optional

            limit:

                * Optional

            offset:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("country", support_from_token=False)
    async def category_playlist(self, *args, **kwargs):
        """
        List playlists from a category

        Arguments:

            category_id:

                * Required

            country:

                * Optional

            limit:

                * Optional

            offset:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def available_genre_seeds(self, *args, **kwargs):
        """
        Available genre seeds

        Arguments:

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("country", support_from_token=False)
    async def featured_playlists(self, *args, **kwargs):
        """
        Featured Playlists

        Arguments:

            country:

                * Optional

            locale:

                * Optional

            timestamp:

                * Optional

            limit:

                * Optional

            offset:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("country", support_from_token=False)
    async def new_releases(self, *args, **kwargs):
        """
        New Releases

        Arguments:

            country:

                * Optional

            limit:

                * Optional

            offset:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("market")
    async def search(self, *args, **kwargs):
        """ 
        Search

        Examples:

            tracks parameter example: ::

                'track' or ['track'] or 'artist' or ['track','artist']

        Arguments:

            q:

                * Query

                * Required

            types:

                * Optional

                * Default: ``'track'``

            market:

                * Optional

            limit:

                * Optional

            offset:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def track_audio_analysis(self, *args, **kwargs):
        """ 
        List audio analysis of a track

        Arguments:

            track_id:

                * Required

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    async def tracks_audio_features(self, *args, **kwargs):
        """ 
        List audio features of tracks

        Arguments:

            track_ids (str, list):

                * Required

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("market", support_from_token=False)
    async def recommendations(self, *args, **kwargs):
        """
        List Recommendations

        https://developer.spotify.com/documentation/web-api/reference/browse/get-recommendations/

        Arguments:

            limit:

                * Optional

            market:

                * Optional

            seed_artists:

                * Optional

            seed_genres:

                * Optional

            seed_tracks:

                * Optional

            min_acousticness:

                * Optional

            max_acousticness:

                * Optional

            target_acousticness:

                * Optional

            min_danceability:

                * Optional

            max_danceability:

                * Optional

            target_danceability:

                * Optional

            min_duration_ms:

                * Optional

            max_duration_ms:

                * Optional

            target_duration_ms:

                * Optional

            min_energy:

                * Optional

            max_energy:

                * Optional

            target_energy:

                * Optional

            min_instrumentalness:

                * Optional

            max_instrumentalness:

                * Optional

            target_instrumentalness:

                * Optional

            min_key:

                * Optional

            max_key:

                * Optional

            target_key:

                * Optional

            min_liveness:

                * Optional

            max_liveness:

                * Optional

            target_liveness:

                * Optional

            min_loudness:

                * Optional

            max_loudness:

                * Optional

            target_loudness:

                * Optional

            min_mode:

                * Optional

            max_mode:

                * Optional

            target_mode:

                * Optional

            min_popularity:

                * Optional

            max_popularity:

                * Optional

            target_popularity:

                * Optional

            min_speechiness:

                * Optional

            max_speechiness:

                * Optional

            target_speechiness:

                * Optional

            min_tempo:

                * Optional

            max_tempo:

                * Optional

            target_tempo:

                * Optional

            min_time_signature:

                * Optional

            max_time_signature:

                * Optional

            target_time_signature:

                * Optional

            min_valence:

                * Optional

            max_valence:

                * Optional

            target_valence:

                * Optional

            to_gather (bool):

                * Whether or not this resource/method will be gathered with ``AsyncSpotify.gather`` or ``AsyncSpotify.gather_now``

                * Optional

                * Default: ``False``

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs
