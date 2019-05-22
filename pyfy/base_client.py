try:
    import ujson as json
except:
    import json
import base64
import warnings
import datetime
from urllib.parse import urlencode

from requests import Request, Response

from .creds import (
    ClientCreds,
    UserCreds,
    _set_empty_client_creds_if_none,
    _set_empty_user_creds_if_none,
)
from .excs import ApiError, AuthError
from .utils import (
    _safe_getitem,
    _get_key_recursively,
    _build_full_url,
    _safe_json_dict,
    _comma_join_list,
    _is_single_resource,
    _convert_to_iso_date,
    _Dict,
)


TOKEN_EXPIRED_MSG = "The access token expired"  # Msg sent back when token is expired
BASE_URI = "https://api.spotify.com/v1"
OAUTH_TOKEN_URL = "https://accounts.spotify.com/api/token"
OAUTH_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"


class _BaseClient:
    """ 
    Serves both Async and Sync clients
    Implements data parsing, building requests and almost all functionality that does not require any IO
    """

    def __init__(
        self,
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
    ):
        """
        Arguments:

            client_creds: A client credentials model

            user_creds: A user credentials model
            
            ensure_user_auth: Whether or not to fail if user_creds provided where invalid and not refresheable
            
            proxies: socks or http proxies # http://docs.python-requests.org/en/master/user/advanced/#proxies & http://docs.python-requests.org/en/master/user/advanced/#socks
            
            timeout: Seconds before request raises a timeout error
            
            max_retries: Max retries before a request fails
            
            backoff_factor: Factor by which requests delays the next request when encountring a 429 too-many-requests error
            
            default_to_locale: Will pass methods decorated with @_default_to_locale the user's locale if available.
            
            cache: Whether or not to cache HTTP requests for the user
        """

        # Credentials models
        self.client_creds = client_creds

        # Request defaults
        self.timeout = timeout

        # Save session attributes for when the user changes
        self.max_retries = max_retries
        self.proxies = proxies
        self.backoff_factor = backoff_factor
        self.cache = cache
        sess = self._create_session(max_retries, proxies, backoff_factor, cache)
        if sess is not None:
            self._session = sess

        # Api defaults
        if enforce_state_check is not None:
            warning_msg = """
            The use of enforce_state_check when constructing a Pyfy client is deprecated. 
            The argument will be removed soon. You should manually validate a user's "state"
            """
            warnings.warn(warning_msg, DeprecationWarning)
        self.enforce_state_check = enforce_state_check
        self.ensure_user_auth = ensure_user_auth
        self.default_to_locale = default_to_locale
        self._populate_user_creds_ = populate_user_creds

        # Set access token then user_creds
        if access_token is not None:
            if user_creds is not None:
                raise ValueError(
                    "Either provide an access token or a user model, not both!"
                )
            else:
                user_creds = UserCreds(access_token=access_token)
        self._user_creds = user_creds

        # Set caller
        if self._user_creds is not None:
            # You shouldn't need to manually change this flag.from_token
            # It's bound to be equal to either the client_creds object or user_creds object depending on which was last authorized
            self._caller = self._user_creds
            if (
                hasattr(user_creds, "access_token")
                and ensure_user_auth
                and self.IS_ASYNC is False
            ):  # Attempt user authorization upon client instantiation
                self._check_authorization()
        elif self.client_creds.access_token:
            self._caller = self.client_creds
        else:
            self._caller = None

    def _prep_authorize_client_creds(self, client_creds=None):
        if client_creds:
            if self.client_creds:
                warnings.warn("Overwriting existing client_creds object")
            self.client_creds = client_creds
        if (
            not self.client_creds
            or not self.client_creds.client_id
            or not self.client_creds.client_secret
        ):
            raise AuthError("No client credentials set")

        data = {"grant_type": "client_credentials"}
        headers = self._client_authorization_header
        return self._create_request(
            method="POST", url=OAUTH_TOKEN_URL, headers=headers, data=data
        )

    def _prep_refresh_user_token(self):
        if not self.user_creds.refresh_token:
            raise AuthError(
                msg="Access token expired and couldn't find a refresh token to refresh it"
            )
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.user_creds.refresh_token,
        }
        headers = {
            **self._client_authorization_header,
            **self._form_url_encoded_type_header,
        }
        return self._create_request(
            method="POST", url=OAUTH_TOKEN_URL, headers=headers, data=data
        )

    def _prep__request_user_creds(self, grant):
        data = {
            "grant_type": "authorization_code",
            "code": grant,
            "redirect_uri": self.client_creds.redirect_uri,
        }
        headers = {
            **self._client_authorization_header,
            **self._form_url_encoded_type_header,
        }
        return self._create_request(
            method="POST", url=OAUTH_TOKEN_URL, headers=headers, data=data
        )

    @property
    def user_creds(self):
        return self._user_creds

    @user_creds.setter
    def user_creds(self, user_creds):
        # Refresh session for each sync user (To avoid cache collision. Not likely. just a precaution).
        if self.IS_ASYNC is False:  # Only if sync.
            self._session.close()
            self._session = self._create_session(
                self.max_retries, self.proxies, self.backoff_factor, self.cache
            )

        # Set user
        self._user_creds = user_creds
        self._caller = self._user_creds

        # Check ensure auth and user popultation (Not allowed for async as this setters shouldn't be coroutines)
        if self.IS_ASYNC is False:
            if self.ensure_user_auth and (
                user_creds.access_token is not None
                or user_creds.refresh_token is not None
            ):
                self._check_authorization()
            if self._populate_user_creds_ and (
                user_creds.access_token is not None
                or user_creds.refresh_token is not None
            ):
                self.populate_user_creds()

    @property
    def is_oauth_ready(self):
        """
        Whether Client Credentials have enough information to perform OAuth2 Authorization Code FLow
        
        Returns

            bool:
        """
        return self.client_creds.is_oauth_ready

    @property
    @_set_empty_user_creds_if_none
    def oauth_uri(self):
        """
        Generate OAuth2 URI for authentication (Deprecated)

        Returns:

            str: OAuth2 Authorizatoin URI
        """
        warnings.warn(
            "oauth_uri property is deprecated in favor of auth_uri() method and will be removed soon",
            DeprecationWarning,
        )
        params = {
            "client_id": self.client_creds.client_id,
            "response_type": "code",
            "scope": " ".join(self.client_creds.scopes),
            "show_dialog": json.dumps(self.client_creds.show_dialog),
        }
        params = urlencode(params)
        redirect_uri = self.client_creds.redirect_uri
        uri = f"{OAUTH_AUTHORIZE_URL}?redirect_uri={redirect_uri}&{params}"
        if self.user_creds.state is not None:
            uri = uri + f"&state={self.user_creds.state}"
        return uri

    def auth_uri(
        self,
        state=None,
        client_id=None,
        scopes=None,
        redirect_uri=None,
        show_dialog=None,
        response_type=None,
    ):
        """
        Generates OAuth2 URI for authentication
        Arguments will default to the attributes of self.client_creds

        Arguments:

            client_id (str): OAuth2 client_id (Defaults to self.client_creds.client_id)

            scopes (list): OAuth2 scopes. (Defaults to self.client_creds.scopes)

            redirect_uri (str): OAuth2 redirect uri. (Defaults to self.client_creds.redirect_uri)

            show_dialog (bool): if set to false, Spotify will not show a new authentication request if user already authorized the client (Defaults to self.client_creds.show_dialog)

            response_type (str): Defaults to "code" for OAuth2 Authorization Code Flow

        Returns:

            str: OAuth2 Auth URI

        """
        client_id = client_id or self.client_creds.client_id
        scopes_list = scopes or self.client_creds.scopes
        redirect_uri = redirect_uri or self.client_creds.redirect_uri
        state = state or getattr(self.user_creds, "state", None)
        show_dialog = show_dialog or self.client_creds.show_dialog or False
        response_type = response_type or "code"

        params = {
            "client_id": client_id,
            "response_type": response_type,
            "scope": " ".join(scopes_list),
            "show_dialog": json.dumps(show_dialog),
        }
        params = urlencode(params)
        uri = f"{OAUTH_AUTHORIZE_URL}?redirect_uri={redirect_uri}&{params}"
        if state is not None:
            uri += f"&state={state}"
        return uri

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
            access_token=json_response["access_token"],
            scopes=json_response["scope"].split(" "),
            expiry=datetime.datetime.utcnow()
            + datetime.timedelta(seconds=json_response["expires_in"]),
            refresh_token=json_response.get("refresh_token", None),
        )

    @staticmethod
    def _client_json_to_object(json_response):
        creds = ClientCreds()
        creds.access_token = json_response["access_token"]
        creds.expiry = datetime.datetime.utcnow() + datetime.timedelta(
            seconds=json_response["expires_in"]
        )
        return creds

    @property
    def _json_content_type_header(self):
        return {"Content-Type": "application/json"}

    @property
    def _form_url_encoded_type_header(self):
        return {"Content-Type": "application/x-www-form-urlencoded"}

    @property
    def _client_authorization_header(self):
        if self.client_creds.client_id and self.client_creds.client_secret:
            # Took me a whole day to figure out that the colon is supposed to be encoded :'(
            utf_header = (
                self.client_creds.client_id + ":" + self.client_creds.client_secret
            )
            return {
                "Authorization": "Basic {}".format(
                    base64.b64encode(utf_header.encode()).decode()
                )
            }
        else:
            raise AttributeError(
                "No client credentials found to make an authorization header"
            )

    @property
    def _client_authorization_data(self):
        return {
            "client_id": self.client_creds.client_id,
            "client_sectet": self.client_creds.client_secret,
        }

    @property
    def _access_authorization_header(self):
        if self._caller is not None:
            return {"Authorization": "Bearer {}".format(self._caller.access_token)}
        else:
            raise ApiError(
                msg="Call Requires an authorized caller, either client or user. Call either authorize_client_creds() or set a user creds object."
            )

    def _create_request(self, method, url, headers={}, data=None, json=None):
        if self.IS_ASYNC is False:
            return Request(
                method=method, headers=headers, url=url, data=data, json=json
            )
        elif self.IS_ASYNC is True:
            return _Dict(
                method=method,
                headers=headers if headers else {},
                url=url,
                data=data
                if data
                else None,  # To avoid sending empty dicts. Aiohttp sometimes gets upset about it.
                json=json if json else None,
            )

    def _prep__check_authorization(self):
        test_url = (
            BASE_URI
            + "/search?"
            + urlencode(dict(q="Hey spotify am I authorized", type="artist"))
        )
        return self._create_request(method="GET", url=test_url)

    def _populate_user_creds(self, me):
        for k, v in me.items():
            if k != "type":  # skip the key named 'type' as it always returns 'user'
                setattr(self.user_creds, k, v)

    ##### Playback

    def _prep_devices(self, **kwargs):
        url = BASE_URI + "/me/player/devices"
        params = dict()
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_play(
        self,
        resource_id=None,
        resource_type="track",
        device_id=None,
        offset_position=None,
        position_ms=None,
        **kwargs,
    ):
        url = BASE_URI + "/me/player/play"
        params = dict(device_id=device_id)
        if resource_id and resource_type:
            context_uri = "spotify:" + resource_type + ":" + resource_id
            if resource_type == "track":
                data = _safe_json_dict(
                    dict(uris=list(context_uri), position_ms=position_ms)
                )
            else:
                data = _safe_json_dict(
                    dict(context_uri=context_uri, position_ms=position_ms)
                )
                if offset_position:
                    offset_data = _safe_json_dict(dict(position=offset_position))
                    if offset_data:
                        data["offset"] = offset_data
        else:
            data = {}

        #    JSON e.g.
        #    {
        #        'context_uri': context_uri, # or uris: [context_uris]
        #        'offset': {
        #            'position': offset_position
        #        },
        #        'position_ms': position_ms
        #    }

        return self._create_request(
            method="PUT", url=_build_full_url(url, params), json=data
        )

    def _prep_pause(self, device_id=None, **kwargs):
        url = BASE_URI + "/me/player/pause"
        params = dict(device_id=device_id)
        return self._create_request(method="PUT", url=_build_full_url(url, params))

    def _prep_currently_playing(self, market=None, **kwargs):
        url = BASE_URI + "/me/player/currently-playing"
        params = dict(market=market)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_currently_playing_info(self, market=None, **kwargs):
        url = BASE_URI + "/me/player"
        params = dict(market=market)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_recently_played_tracks(
        self, limit=None, after=None, before=None, **kwargs
    ):
        url = BASE_URI + "/me/player/recently-played"
        params = dict(type="track", limit=limit, after=after, before=before)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_next(self, device_id=None, **kwargs):
        url = BASE_URI + "/me/player/next"
        params = dict(device_id=device_id)
        return self._create_request(method="POST", url=_build_full_url(url, params))

    def _prep_previous(self, device_id=None, **kwargs):
        url = BASE_URI + "/me/player/previous"
        params = dict(device_id=device_id)
        return self._create_request(method="POST", url=_build_full_url(url, params))

    def _prep_repeat(self, state="context", device_id=None, **kwargs):
        url = BASE_URI + "/me/player/repeat"
        params = dict(state=state, device_id=device_id)
        return self._create_request(method="PUT", url=_build_full_url(url, params))

    def _prep_seek(self, position_ms, device_id=None, **kwargs):
        url = BASE_URI + "/me/player/seek"
        params = dict(position_ms=position_ms, device_id=device_id)
        return self._create_request(method="PUT", url=_build_full_url(url, params))

    def _prep_shuffle(self, state=True, device_id=None, **kwargs):
        url = BASE_URI + "/me/player/shuffle"
        params = dict(state=state, device_id=device_id)
        return self._create_request(method="PUT", url=_build_full_url(url, params))

    def _prep_playback_transfer(self, device_ids, **kwargs):
        url = BASE_URI + "/me/player"
        params = {}
        data = _safe_json_dict(dict(device_ids=_comma_join_list(device_ids)))
        return self._create_request(
            method="PUT", url=_build_full_url(url, params), json=data
        )

    def _prep_volume(self, volume_percent, device_id=None, **kwargs):
        url = BASE_URI + "/me/player/volume"
        params = dict(volume_percent=volume_percent, device_id=device_id)
        return self._create_request(method="PUT", url=_build_full_url(url, params))

    ##### Playlists

    def _prep_playlist(self, playlist_id, market=None, fields=None, **kwargs):
        url = BASE_URI + "/playlists/" + playlist_id
        params = dict(market=market, fields=fields)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_user_playlists(self, user_id=None, limit=None, offset=None, **kwargs):
        if user_id is None:
            return self._prep__user_playlists(limit=limit, offset=offset)
        url = BASE_URI + "/users/" + user_id + "/playlists"
        params = dict(limit=limit, offset=offset)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep__user_playlists(self, limit=None, offset=None, **kwargs):
        url = BASE_URI + "/me/playlists"
        params = dict(limit=limit, offset=offset)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_follows_playlist(
        self, playlist_id, user_ids=None, user_id=None, **kwargs
    ):
        if user_ids is None:
            user_ids = user_id
        url = BASE_URI + "/playlists/" + playlist_id + "/followers/contains"
        params = dict(ids=_comma_join_list(user_ids))
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_create_playlist(
        self,
        name,
        description=None,
        public=False,
        collaborative=False,
        user_id=None,
        **kwargs,
    ):
        url = BASE_URI + "/users/" + user_id + "/playlists"
        params = {}
        data = dict(
            name=name,
            description=description,
            public=public,
            collaborative=collaborative,
        )
        return self._create_request(
            method="POST", url=_build_full_url(url, params), json=_safe_json_dict(data)
        )

    def _prep_follow_playlist(self, playlist_id, public=None, **kwargs):
        url = BASE_URI + "/playlists/" + playlist_id + "/followers"
        params = {}
        data = _safe_json_dict(dict(public=public))
        return self._create_request(
            method="PUT", url=_build_full_url(url, params), json=data
        )

    def _prep_update_playlist(
        self,
        playlist_id,
        name=None,
        description=None,
        public=None,
        collaborative=False,
        **kwargs,
    ):
        url = BASE_URI + "/playlists/" + playlist_id
        params = {}
        data = dict(
            name=name,
            description=description,
            public=public,
            collaborative=collaborative,
        )
        return self._create_request(
            method="PUT", url=_build_full_url(url, params), json=_safe_json_dict(data)
        )
        r.headers.update(self._json_content_type_header)

    def _prep_unfollow_playlist(self, playlist_id, **kwargs):
        url = BASE_URI + "/playlists/" + playlist_id + "/followers"
        params = {}
        return self._create_request(method="DELETE", url=_build_full_url(url, params))

    def _prep_delete_playlist(self, playlist_id, **kwargs):
        """ an alias to unfollow_playlist"""
        return self._prep_unfollow_playlist(playlist_id)

    ##### Playlist Contents

    def _prep_playlist_tracks(
        self, playlist_id, market=None, fields=None, limit=None, offset=None, **kwargs
    ):
        url = BASE_URI + "/playlists/" + playlist_id + "/tracks"
        params = dict(market=market, fields=fields, limit=limit, offset=offset)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_add_playlist_tracks(
        self, playlist_id, track_ids, position=None, **kwargs
    ):
        url = BASE_URI + "/playlists/" + playlist_id + "/tracks"

        # convert IDs to uris. WHY SPOTIFY :(( ?
        if type(track_ids) == str:
            track_ids = [track_ids]
        new_list = []
        for track_id in track_ids:
            new_list.append("spotify:track:" + track_id)

        params = dict(position=position, uris=_comma_join_list(new_list))
        return self._create_request(method="POST", url=_build_full_url(url, params))

    def _prep_reorder_playlist_track(
        self,
        playlist_id,
        range_start=None,
        range_length=None,
        insert_before=None,
        **kwargs,
    ):
        url = BASE_URI + "/playlists/" + playlist_id + "/tracks"
        params = {}
        data = dict(
            range_start=range_start,
            range_length=range_length,
            insert_before=insert_before,
        )
        return self._create_request(
            method="PUT", url=_build_full_url(url, params), json=_safe_json_dict(data)
        )

    def _prep_delete_playlist_tracks(self, playlist_id, track_ids, **kwargs):
        """ 
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
        """
        # https://developer.spotify.com/console/delete-playlist-tracks/
        url = BASE_URI + "/playlists/" + playlist_id + "/tracks"
        params = {}
        if type(track_ids) == str:
            track_ids = list(track_ids)
        elif type(track_ids) == list:
            data = {"tracks": []}
            for track_id in track_ids:
                if type(track_id) == str:
                    data["tracks"].append({"uri": "spotify:track:" + track_id})
                elif type(track_id) == dict:
                    positions = track_id.get("positions")
                    if type(positions) == str or int:
                        positions = [positions]
                    data["tracks"].append(
                        {
                            "uri": "spotify:track:" + track_id["id"],
                            "positions": positions,
                        }
                    )
        else:
            raise TypeError("track_ids must be an instance of list or string")
        return self._create_request(
            method="DELETE", url=_build_full_url(url, params), json=data
        )

    #### Tracks

    def _prep_user_tracks(self, market=None, limit=None, offset=None, **kwargs):
        url = BASE_URI + "/me/tracks"
        params = dict(market=market, limit=limit, offset=offset)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_tracks(self, track_ids, market=None, **kwargs):
        if _is_single_resource(track_ids):
            return self._prep__track(
                track_id=_comma_join_list(track_ids), market=market
            )
        url = BASE_URI + "/tracks"
        params = dict(ids=_comma_join_list(track_ids), market=market)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep__track(self, track_id, market=None, **kwargs):
        url = BASE_URI + "/tracks/" + track_id
        params = dict(market=market)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_owns_tracks(self, track_ids, **kwargs):
        url = BASE_URI + "/me/tracks/contains"
        params = dict(ids=_comma_join_list(track_ids))
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_save_tracks(self, track_ids, **kwargs):
        url = BASE_URI + "/me/tracks"
        params = dict(ids=_comma_join_list(track_ids))
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_delete_tracks(self, track_ids, **kwargs):
        url = BASE_URI + "/me/tracks"
        params = dict(ids=_comma_join_list(track_ids))
        return self._create_request(method="DELETE", url=_build_full_url(url, params))

    ##### Artists

    def _prep_artists(self, artist_ids, **kwargs):
        if _is_single_resource(artist_ids):
            return self._prep__artist(_comma_join_list(artist_ids))
        url = BASE_URI + "/artists"
        params = dict(ids=_comma_join_list(artist_ids))
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep__artist(self, artist_id, **kwargs):
        url = BASE_URI + "/artists/" + artist_id
        params = dict()
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_followed_artists(self, after=None, limit=None, **kwargs):
        url = BASE_URI + "/me/following"
        params = dict(type="artist", after=after, limit=limit)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_follows_artists(self, artist_ids, **kwargs):
        url = BASE_URI + "/me/following/contains"
        params = dict(type="artist", ids=_comma_join_list(artist_ids))
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_follow_artists(self, artist_ids, **kwargs):
        url = BASE_URI + "/me/following"
        params = dict(type="artist", ids=_comma_join_list(artist_ids))
        return self._create_request(method="PUT", url=_build_full_url(url, params))

    def _prep_unfollow_artists(self, artist_ids, **kwargs):
        url = BASE_URI + "/me/following"
        params = dict(type="artist", ids=_comma_join_list(artist_ids))
        return self._create_request(method="DELETE", url=_build_full_url(url, params))

    def _prep_artist_related_artists(self, artist_id, **kwargs):
        url = BASE_URI + "/artists/" + artist_id + "/related-artists"
        params = {}
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_artist_top_tracks(self, artist_id, country=None, **kwargs):
        url = BASE_URI + "/artists/" + artist_id + "/top-tracks"
        params = dict(country=country)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    ##### Albums

    def _prep_albums(self, album_ids, market=None, **kwargs):
        if _is_single_resource(album_ids):
            return self._prep__album(_comma_join_list(album_ids), market)
        url = BASE_URI + "/albums"
        params = dict(ids=_comma_join_list(album_ids), market=market)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep__album(self, album_id, market=None, **kwargs):
        url = BASE_URI + "/albums/" + album_id
        params = dict(market=market)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_user_albums(self, limit=None, offset=None, **kwargs):
        url = BASE_URI + "/me/albums"
        params = dict(limit=limit, offset=offset)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_owns_albums(self, album_ids, **kwargs):
        url = BASE_URI + "/me/albums/contains"
        params = dict(ids=_comma_join_list(album_ids))
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_save_albums(self, album_ids, **kwargs):
        url = BASE_URI + "/me/albums"
        params = dict(ids=_comma_join_list(album_ids))
        return self._create_request(method="PUT", url=_build_full_url(url, params))

    def _prep_delete_albums(self, album_ids, **kwargs):
        url = BASE_URI + "/me/albums"
        params = dict(ids=_comma_join_list(album_ids))
        return self._create_request(method="DELETE", url=_build_full_url(url, params))

    ##### Users

    def _prep_me(self, **kwargs):
        url = BASE_URI + "/me"
        return self._create_request(method="GET", url=url)

    def _prep_user_profile(self, user_id, **kwargs):
        url = BASE_URI + "/users/" + user_id
        params = dict()
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_follows_users(self, user_ids, **kwargs):
        url = BASE_URI + "/me/following/contains"
        params = dict(type="user", ids=_comma_join_list(user_ids))
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_follow_users(self, user_ids, **kwargs):
        url = BASE_URI + "/me/following"
        params = dict(type="user", ids=_comma_join_list(user_ids))
        return self._create_request(method="PUT", url=_build_full_url(url, params))

    def _prep_unfollow_users(self, user_ids, **kwargs):
        url = BASE_URI + "/me/following"
        params = dict(type="user", ids=_comma_join_list(user_ids))
        return self._create_request(method="DELETE", url=_build_full_url(url, params))

    ##### Others

    def _prep_album_tracks(
        self, album_id, market=None, limit=None, offset=None, **kwargs
    ):
        url = BASE_URI + "/albums/" + album_id + "/tracks"
        params = dict(market=market, limit=limit, offset=offset)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_artist_albums(
        self,
        artist_id,
        include_groups=None,
        market=None,
        limit=None,
        offset=None,
        **kwargs,
    ):
        url = BASE_URI + "/artists/" + artist_id + "/albums"
        params = dict(
            include_groups=include_groups, market=market, limit=limit, offset=offset
        )
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_user_top_tracks(self, time_range=None, limit=None, offset=None, **kwargs):
        url = BASE_URI + "/me/top/tracks"
        params = dict(time_range=time_range, limit=limit, offset=offset)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_user_top_artists(
        self, time_range=None, limit=None, offset=None, **kwargs
    ):
        url = BASE_URI + "/me/top/artists"
        params = dict(time_range=time_range, limit=limit, offset=offset)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_next_page(self, response=None, url=None, **kwargs):
        if url is None:
            url = _get_key_recursively(response, "next", 3)
        if url is not None:
            return self._create_request(method="GET", url=url)
        return None

    def _prep_previous_page(self, response=None, url=None, **kwargs):
        if url is None:
            url = _get_key_recursively(response, "previous", 3)
        if url is not None:
            return self._create_request(method="GET", url=url)
        return None

    ##### Personalization & Explore

    def _prep_category(self, category_id, country=None, locale=None, **kwargs):
        url = BASE_URI + "/browse/categories/" + category_id
        params = dict(country=country, locale=locale)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_categories(
        self, country=None, locale=None, limit=None, offset=None, **kwargs
    ):
        url = BASE_URI + "/browse/categories"
        params = dict(country=country, locale=locale, limit=limit, offset=offset)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_category_playlist(
        self, category_id, country=None, limit=None, offset=None, **kwargs
    ):
        url = BASE_URI + "/browse/categories/" + category_id + "/playlists"
        params = dict(country=country, limit=limit, offset=offset)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_available_genre_seeds(self, **kwargs):
        return self._create_request(
            method="GET", url=BASE_URI + "/recommendations/available-genre-seeds"
        )

    def _prep_featured_playlists(
        self,
        country=None,
        locale=None,
        timestamp=None,
        limit=None,
        offset=None,
        **kwargs,
    ):
        if isinstance(timestamp, datetime.datetime):
            timestamp = _convert_to_iso_date(timestamp)
        url = BASE_URI + "/browse/featured-playlists"
        params = dict(
            country=country,
            locale=locale,
            timestamp=timestamp,
            limit=limit,
            offset=offset,
        )
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_new_releases(self, country=None, limit=None, offset=None, **kwargs):
        url = BASE_URI + "/browse/new-releases"
        params = dict(country=country, limit=limit, offset=offset)
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_search(
        self, q, types="track", market=None, limit=None, offset=None, **kwargs
    ):
        """ 'track' or ['track'] or 'artist' or ['track','artist'] """
        url = BASE_URI + "/search"
        params = dict(
            q=q, type=_comma_join_list(types), market=market, limit=limit, offset=offset
        )
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_track_audio_analysis(self, track_id, **kwargs):
        url = BASE_URI + "/audio-analysis/" + track_id
        params = {}
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_tracks_audio_features(self, track_ids, **kwargs):
        if _is_single_resource(track_ids):
            return self._prep__track_audio_features(_comma_join_list(track_ids))
        url = BASE_URI + "/audio-features"
        params = dict(ids=_comma_join_list(track_ids))
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep__track_audio_features(self, track_id, **kwargs):
        url = BASE_URI + "/audio-features/" + track_id
        params = dict()
        return self._create_request(method="GET", url=_build_full_url(url, params))

    def _prep_recommendations(
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
        **kwargs,
    ):
        """ https://developer.spotify.com/documentation/web-api/reference/browse/get-recommendations/ """
        url = BASE_URI + "/recommendations"
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
            target_valence=target_valence,
        )
        return self._create_request(method="GET", url=_build_full_url(url, params))
