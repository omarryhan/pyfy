import logging
import datetime
from urllib import parse
from urllib3.util import Retry
import warnings

from requests import Request, Session, Response
from requests.exceptions import HTTPError, Timeout
from requests.adapters import HTTPAdapter
from cachecontrol import CacheControlAdapter

from .creds import ClientCreds, _set_empty_user_creds_if_none
from .excs import ApiError, AuthError
from .utils import _safe_getitem
from .wrappers import (
    _dispatch_request,
    _set_and_get_me_attr_sync,
    _default_to_locale,
    _inject_user_id,
)
from .base_client import _BaseClient, TOKEN_EXPIRED_MSG, BASE_URI


logger = logging.getLogger(__name__)


class Spotify(_BaseClient):
    """
    Spotify's Synchronous Client
    
    Arguments:
        
        client_creds (pyfy.creds.ClientCreds): A client credentials model
        
        user_creds (pyfy.creds.UserCreds): A user credentials model
        
        ensure_user_auth (bool):
        
            * Whether or not to fail upon instantiation if user_creds provided where invalid and not refresheable.
            
            * Default: False
    
        proxies: 
        
            * socks or http proxies
            
            * http://docs.python-requests.org/en/master/user/advanced/#proxies & http://docs.python-requests.org/en/master/user/advanced/#socks
        
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
        
        cache: 
        
            * Whether or not to cache HTTP requests for the user

            * Default: True
    
        populate_user_creds (bool):
        
            * Sets user_creds info from Spotify to client's user_creds object. e.g. country.

            * Default: True
    """

    IS_ASYNC = False

    def __init__(
        self,
        access_token=None,
        client_creds=ClientCreds(),
        user_creds=None,
        ensure_user_auth=False,
        proxies={},
        timeout=7,
        max_retries=10,
        enforce_state_check=None,
        backoff_factor=0.1,
        default_to_locale=True,
        cache=True,
        populate_user_creds=True,
    ):
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
        if populate_user_creds and self.user_creds:
            self.populate_user_creds()

    def populate_user_creds(self):
        """ 
        Populates self.user_creds with Spotify's info on user.
        Data is fetched from self.me() and set to user recursively
        """
        me = self.me()
        if me:
            self._populate_user_creds(me)

    def _create_session(self, max_retries, proxies, backoff_factor, cache):
        sess = Session()
        # Retry only on idempotent methods and only when too many requests
        retries = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429],
            method_whitelist=["GET", "UPDATE", "DELETE"],
        )
        retries_adapter = HTTPAdapter(max_retries=retries)
        if cache:
            cache_adapter = CacheControlAdapter(cache_etags=True)
        sess.mount("http://", retries_adapter)
        sess.mount("http://", cache_adapter)
        sess.proxies.update(proxies)
        return sess

    @_dispatch_request
    def _check_authorization(self):
        """
        Checks whether the credentials provided are valid or not by making and api call that requires no scope but still requires authorization
        """
        return list(), dict()

    def _send_authorized_request(self, r):
        if (
            getattr(self._caller, "access_is_expired", None) is True
        ):  # True if expired and None if there's no expiry set
            self._refresh_token()
        r.headers.update(self._access_authorization_header)
        return self._send_request(r)

    def _send_request(self, r):
        prepped = r.prepare()
        logger.debug(r.url)
        try:
            res = self._session.send(prepped, timeout=self.timeout)
            res.raise_for_status()
        except Timeout as e:
            raise ApiError(
                "Request timed out.\nTry increasing the client's timeout period",
                http_response=Response(),
                http_request=r,
                e=e,
            )
        except HTTPError as e:
            if res.status_code == 401:
                if (
                    res.json().get("error", None).get("message", None)
                    == TOKEN_EXPIRED_MSG
                ):
                    old_auth_header = r.headers["Authorization"]
                    self._refresh_token()  # Should either raise an error or refresh the token
                    new_auth_header = self._access_authorization_header
                    if new_auth_header == old_auth_header:
                        msg = "refresh_token() was successfully called but token wasn't refreshed. Execution stopped to avoid infinite looping."
                        logger.critical(msg)
                        raise RuntimeError(msg)
                    r.headers.update(new_auth_header)
                    return self._send_request(r)
                else:
                    msg = res.json().get("error_description") or res.json()
                    raise AuthError(msg=msg, http_response=res, http_request=r, e=e)
            else:
                msg = _safe_getitem(res.json(), "error", "message") or _safe_getitem(
                    res.json(), "error_description"
                )
                raise ApiError(msg=msg, http_response=res, http_request=r, e=e)
        else:
            return res

    def authorize_client_creds(self, client_creds=None):
        """ 
        Authorize with client credentials oauth flow i.e. Only with client secret and client id.

        Call this to send request using client credentials.
        
        https://developer.spotify.com/documentation/general/guides/authorization-guide/ 
        
        Note:

            This will give you limited access to most endpoints

        Arguments:

            client_creds (pyfy.creds.ClientCreds): Client Credentials object. Defaults to ``self.client_creds``.

        Raises:

            pyfy.excs.AuthErrror: 
        """
        r = self._prep_authorize_client_creds(client_creds)
        try:
            res = self._send_request(r)
        except ApiError as e:
            raise AuthError(
                msg="Failed to authenticate with client credentials",
                http_response=e.http_response,
                http_request=r,
                e=e,
            )
        else:
            new_creds_json = res.json()
            new_creds_model = self._client_json_to_object(new_creds_json)
            self._update_client_creds_with(new_creds_model)
            self._caller = self.client_creds
            self._check_authorization()

    @property
    def is_active(self):
        """
        Checks if user_creds or client_creds are valid (depending on who was last set)
        """
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
            raise AuthError("No caller to refresh token for")

    def _refresh_user_token(self):
        r = self._prep_refresh_user_token()
        res = self._send_request(r).json()
        new_creds_obj = self._user_json_to_object(res)
        self._update_user_creds_with(new_creds_obj)

    @_set_empty_user_creds_if_none
    def build_user_creds(
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
        user_creds_json = self._request_user_creds(grant)
        user_creds_model = self._user_json_to_object(user_creds_json)

        # Set user creds
        if set_user_creds:
            self.user_creds = user_creds_model
        return user_creds_model

    @property
    def is_premium(self, **kwargs):
        """
        Checks whether user is premium or not

        Returns:

            bool:
        """
        if _set_and_get_me_attr_sync(self, "product") == "premium":
            return True
        return False

    @_dispatch_request(authorized_request=False)
    def _request_user_creds(self, grant):
        return [grant], dict()

    ####################################################################### RESOURCES ############################################################################

    ##### Playback
    @_dispatch_request
    def devices(self, *args, **kwargs):
        """
        Lists user's devices

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def play(self, *args, **kwargs):
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

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def pause(self, *args, **kwargs):
        """
        Pauses playback

        Arguments:

            device_id (str):

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("market")
    def currently_playing(self, *args, **kwargs):
        """
        Lists currenly playing

        Arguments:

            market (str):

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("market")
    def currently_playing_info(self, *args, **kwargs):
        """
        Lists currently playing info

        Arguments:

            market (str):

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def recently_played_tracks(self, *args, **kwargs):
        """
        Lists recently played tracks

        Arguments:

            limit (int):

                * Optional

            after:

                * Optional

            before:

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def next(self, *args, **kwargs):
        """
        Next playback

        Arguments:

            device_id:

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def previous(self, *args, **kwargs):
        """
        Previous Playback

        Arguments:

            device_id:

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def repeat(self, *args, **kwargs):
        """
        Toggle repeat

        Arguments:

            state:

                * Optional

                * Default: 'context'

            device_id:

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def seek(self, *args, **kwargs):
        """
        Seek Playback

        Arguments:

            posiotion_ms:

                * Required

            device_id:

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def shuffle(self, *args, **kwargs):
        """
        Shuffle Playback

        Arguments:

            state:

                * Optional

                * Default: True

            device_id:

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def playback_transfer(self, *args, **kwargs):
        """
        Transfer playback to another device

        Arguments:

            device_ids (list, str):

                * Required

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def volume(self, *args, **kwargs):
        """
        Change volume

        Arguments:

            volume_percent (int):

                * Required

            device_id:

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    ##### Playlists

    @_dispatch_request
    @_default_to_locale("market")
    def playlist(self, *args, **kwargs):
        """
        Lists playlist

        Arguments:

            playlist_id:

                * Required

            market:

                * Optional

            fields:

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def user_playlists(self, *args, **kwargs):
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

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_inject_user_id
    def follows_playlist(self, *args, **kwargs):
        """
        Lists whether or not user follows a playlist

        Arguments:

            playlist_id:

                * Required

            user_ids (list, str):

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_inject_user_id
    def create_playlist(self, *args, **kwargs):
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

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def follow_playlist(self, *args, **kwargs):
        """
        Follows a playlist

        Arguments:

            playlist_id:

                * Required

            public:

                * Optional

                * Default: False

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def update_playlist(self, *args, **kwargs):
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

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def unfollow_playlist(self, *args, **kwargs):
        """
        Unfollow a playlist

        Arguments:

            playlist_id:

                * Required

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def delete_playlist(self, *args, **kwargs):
        """
        An alias to unfollow_playlist

        Arguments:

            playlist_id:

                * Required

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    ##### Playlist Contents

    @_dispatch_request
    @_default_to_locale("market")
    def playlist_tracks(self, *args, **kwargs):
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

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def add_playlist_tracks(self, *args, **kwargs):
        """
        Add tracks to a playlist

        Arguments:

            playlist_id:

                * Required

            track_ids (str, list):

                * Required

            position:

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def reorder_playlist_track(self, *args, **kwargs):
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

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def delete_playlist_tracks(self, *args, **kwargs):
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

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    ##### Tracks

    @_dispatch_request
    @_default_to_locale("market")
    def user_tracks(self, *args, **kwargs):
        """
        List user's tracks

        Arguments:

            market:

                * Optional

            limit:

                * Optional

            offset:

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("market")
    def tracks(self, *args, **kwargs):
        """
        List tracks

        Arguments:

            track_ids (str, list):

                * Required

            market:

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def owns_tracks(self, *args, **kwargs):
        """
        Lists whether or not current user owns tracks

        Arguments:

            track_ids (str, list):

                * Required

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def save_tracks(self, *args, **kwargs):
        """
        Save tracks

        Arguments:

            track_ids (str, list):

                * Required

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def delete_tracks(self, *args, **kwargs):
        """
        Delete user's tracks

        Arguments:

            track_ids (str, list):


        Returns:

            dict:
                * Required
        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    ##### Artists

    @_dispatch_request
    def artists(self, *args, **kwargs):
        """
        List artists

        Arguments:

            artist_ids (str, list):


        Returns:

            dict:
                * Required
        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def followed_artists(self, *args, **kwargs):
        """
        List artists followed by current user

        Arguments:

            after:

                * Optional

            limit:

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def follows_artists(self, *args, **kwargs):
        """
        Whether or not current user follows an artist(s)

        Arguments:

            artist_ids (str, list):

                * Required

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def follow_artists(self, *args, **kwargs):
        """
        Follow an artist(s)

        Arguments:

            artist_ids (str, list):

                * Required

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def unfollow_artists(self, *args, **kwargs):
        """
        Unfollow artist(s)

        Arguments:

            artist_ids (str, list):

                * Required

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def artist_related_artists(self, *args, **kwargs):
        """
        List artists related to an artist

        Arguments:

            artist_id (str):

                * Required

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("country")
    def artist_top_tracks(self, *args, **kwargs):
        """
        List top tracks of an artist

        Arguments:

            artist_id (str):

                * Required

            country:

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    ##### Albums

    @_dispatch_request
    @_default_to_locale("market")
    def albums(self, *args, **kwargs):
        """
        List Albums

        Arguments:

            album_ids (str, list):

                * Required

            market:

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def user_albums(self, *args, **kwargs):
        """
        Albums owned by current user

        Arguments:

            limit:

                * Optional

            offset:

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def owns_albums(self, *args, **kwargs):
        """
        Whether or not current user owns an album(s)

        Arguments:

            album_ids (str, list):

                * Required

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def save_albums(self, *args, **kwargs):
        """
        Save Albums

        Arguments:

            album_ids (str, list):

                * Required

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def delete_albums(self, *args, **kwargs):
        """
        Delete Albums

        Arguments:

            album_ids (str, list):

                * Required

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    ##### Users

    @_dispatch_request
    def me(self, *args, **kwargs):
        """
        List current user's profile

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def user_profile(self, *args, **kwargs):
        """
        List a user's profile

        Arguments:

            user_id (str):

                * Required

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def follows_users(self, *args, **kwargs):
        """
        Whether or not current user follows a user(s)

        Arguments:

            user_ids (str, list):

                * Required

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def follow_users(self, *args, **kwargs):
        """
        Follow a user

        Arguments:

            user_ids (str, list):

                * Required

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def unfollow_users(self, *args, **kwargs):
        """
        Unfollow user(s)

        Arguments:

            user_ids (str, list):

                * Required

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    ##### Others

    @_dispatch_request
    @_default_to_locale("market")
    def album_tracks(self, *args, **kwargs):
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

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("market")
    def artist_albums(self, *args, **kwargs):
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

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def user_top_tracks(self, *args, **kwargs):
        """
        List top tracks of a user

        Arguments:

            time_range:

                * Optional

            limit:

                * Optional

            offset:

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def user_top_artists(self, *args, **kwargs):
        """
        List top artists of a user

        Arguments:

            time_range:

                * Optional

            limit:

                * Optional

            offset:

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def next_page(self, *args, **kwargs):
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

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def previous_page(self, *args, **kwargs):
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

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    ##### Personalization & Explore

    @_dispatch_request
    @_default_to_locale("country", support_from_token=False)
    def category(self, *args, **kwargs):
        """
        List Category

        Arguments:

            category_id:

                * Required

            country:

                * Optional

            locale:

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("country", support_from_token=False)
    def categories(self, *args, **kwargs):
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

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("country", support_from_token=False)
    def category_playlist(self, *args, **kwargs):
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

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def available_genre_seeds(self, *args, **kwargs):
        """
        Available genre seeds

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("country", support_from_token=False)
    def featured_playlists(self, *args, **kwargs):
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

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("country", support_from_token=False)
    def new_releases(self, *args, **kwargs):
        """
        New Releases

        Arguments:

            country:

                * Optional

            limit:

                * Optional

            offset:

                * Optional

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("market")
    def search(self, *args, **kwargs):
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

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def track_audio_analysis(self, *args, **kwargs):
        """ 
        List audio analysis of a track

        Arguments:

            track_id:

                * Required

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    def tracks_audio_features(self, *args, **kwargs):
        """ 
        List audio features of tracks

        Arguments:

            track_ids (str, list):

                * Required

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs

    @_dispatch_request
    @_default_to_locale("market", support_from_token=False)
    def recommendations(self, *args, **kwargs):
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

        Returns:

            dict:

        Raises:

            pyfy.excs.ApiError:
        """
        return args, kwargs
