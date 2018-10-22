from pprint import pprint, pformat
import json
import logging
import warnings
import datetime
from urllib import parse
import asyncio

from aiohttp import ClientSession, ClientTimeout, ClientRequest, ClientResponseError, ClientError
from concurrent.futures._base import TimeoutError
import backoff

from .creds import (
    ClientCreds,
    UserCreds,
    ALL_SCOPES,
    _set_empty_user_creds_if_none
)
from .excs import SpotifyError, ApiError, AuthError
from .utils import (
    _safe_getitem,
    _get_key_recursively,
    _locale_injectable,
    _nullable_response,
    _build_full_url,
    _safe_json_dict,
    _comma_join_list,
    _is_single_resource,
    _convert_to_iso_date,
    _prep_request,
    _resolve_async_response,
    _resolve_response
)
from.base_client import (
    BaseClient,
    TOKEN_EXPIRED_MSG,
    BASE_URI,
    OAUTH_TOKEN_URL,
    OAUTH_AUTHORIZE_URL
)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class AsyncSpotify(BaseClient):
    def __init__(self, access_token=None, client_creds=ClientCreds(), user_creds=None, proxies=None, proxy_auth=None, timeout=7,
                max_retries=1, enforce_state_check=True, backoff_factor=1, default_to_locale=True, populate_user_creds=True):
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
        ''' populates self.user_creds with Spotify's info on user
        Data is fetched from self.me and set to user recursively '''
        me = await self.me
        if me:
            self._populate_user_creds(me)

    def _create_session(self, cache=None, proxies=None, backoff_factor=None, max_retries=None):
        ''' Warning: Creating a client session outside of a coroutine is a very dangerous idea. See:
        https://github.com/aio-libs/aiohttp/pull/3078/commits/34b3520bc9966ee4ec41b70257960e01d86d5978 '''
        return None

    @property
    def Session(self):
        #timeout = ClientTimeout(total=self.timeout)
        #return lambda: ClientSession(timeout=timeout)
        return ClientSession

    async def _send_authorized_request(self, r):
        if getattr(self._caller, 'access_is_expired', None) is True:  # True if expired and None if there's no expiry set
            await self._refresh_token()
        r['headers'].update(self._access_authorization_header)
        return await self._send_request(r)

    async def _send_request(self, r):
        # workaround to support setting instance specific timeouts and maxretries
        return await backoff.on_exception(
            wait_gen=lambda: backoff.expo(factor=self.backoff_factor),
            exception=(TimeoutError, asyncio.TimeoutError),  # Not sure why this isn't working properly???
            max_tries=self.max_retries,
            max_time=self.timeout
        )(self._handle_send_request)(r)

    async def _handle_send_request(self, r):
        #print('\n\n REQUEST:')
        #pprint(r.__dict__)
        async with self.Session() as sess:
            res = await sess.request(
                url=r.get('url'),
                headers=r.get('headers'),
                data=r.get('data'),
                json=r.get('json'),
                method=r.get('method'),
                proxy=self.proxies,
                proxy_auth=self.proxy_auth,
                timeout=ClientTimeout(total=self.timeout + 1)  # To make it retry first
            )
        try:
            #if res.status == 204:  # No content
            #    new_res = _resolve_response(res)
            #else:
            #    new_res = await _resolve_async_response(res)
            new_res = await _resolve_async_response(res)
            #print('\n\n RESPONSE:')
            #pprint(res.__dict__.get('json'))
            res.raise_for_status()
        except (TimeoutError, asyncio.TimeoutError) as e:
            print('\nRequest timed out, try increasing the timeout period\n')
            raise e
        except ClientResponseError as e:
            if new_res.status_code == 401:
                if new_res.json.get('error', None).get('message', None) == TOKEN_EXPIRED_MSG:
                    old_auth_header = r['headers']['Authorization']
                    await self._refresh_token()  # Should either raise an error or refresh the token
                    new_auth_header = self._access_authorization_header
                    assert new_auth_header != old_auth_header  # Assert access token is changed to avoid infinite loops
                    r['headers'].update(new_auth_header)
                    new_res = await self._send_request(r)
                else:
                    msg = new_res.json.get('error_description') or new_res.json  # If none, raise the whole JSON
                    raise AuthError(msg=msg, http_response=new_res, http_request=r, e=e)
            elif new_res.status_code == 429:
                retry_after = new_res.headers['Retry-After']
                asyncio.sleep(retry_after)
                new_res = await self._handle_send_request(r)
                return new_res
            else:
                msg = _safe_getitem(new_res.json, 'error', 'message') or _safe_getitem(new_res.json, 'error_description')
                raise ApiError(msg=msg, http_response=new_res, http_request=r, e=e)
        else:
            return new_res

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
        res = await self._send_request(r)
        json_res = res.json
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
        self._check_for_state(grant, state, set_user_creds)

        # Get user creds
        user_creds_json = (await self._request_user_creds(grant)).json
        user_creds_model = self._user_json_to_object(user_creds_json)

        # Set user creds
        if set_user_creds:
            self.user_creds = user_creds_model
        return user_creds_model

    @_prep_request
    async def _request_user_creds(self, grant, **kwargs):
        return await self._send_request(kwargs['r'])

################################################# Resources #####################################################

##### Playback
    @_prep_request
    async def devices(self, **kwargs):
        ''' Lists user's devices '''
        return (await self._send_authorized_request(kwargs['r'])).json

    #@_nullable_response
    @_prep_request
    async def play(self, resource_id=None, resource_type='track', device_id=None, offset_position=None, position_ms=None, **kwargs):
        ''' Available types: 'track', 'artist', 'playlist', 'podcast', 'user' not sure if there's more'''
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def pause(self, device_id=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def currently_playing(self, market=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def currently_playing_info(self, market=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def recently_played_tracks(self, limit=None, after=None, before=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def next(self, device_id=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def previous(self, device_id=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def repeat(self, state='context', device_id=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def seek(self, position_ms, device_id=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def shuffle(self, state=True, device_id=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def playback_transfer(self, device_ids, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def volume(self, volume_percent, device_id=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

##### Playlists

    @_prep_request
    async def playlist(self, playlist_id, market=None, fields=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def user_playlists(self, user_id=None, limit=None, offset=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def _user_playlists(self, limit=None, offset=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

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
        return (await self._send_authorized_request(r)).json

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
        return (await self._send_authorized_request(r)).json

    @_nullable_response
    @_prep_request
    async def follow_playlist(self, playlist_id, public=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def update_playlist(self, playlist_id, name=None, description=None, public=None, collaborative=False, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def unfollow_playlist(self, playlist_id, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def delete_playlist(self, playlist_id, **kwargs):
        ''' an alias to unfollow_playlist''' 
        return (await self._send_authorized_request(kwargs['r'])).json


##### Playlist Contents

    @_prep_request
    async def playlist_tracks(self, playlist_id, market=None, fields=None, limit=None, offset=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def add_playlist_tracks(self, playlist_id, track_ids, position=None, **kwargs):
        ''' track_ids can be a list of track ids or a string of one track_id'''
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def reorder_playlist_track(self, playlist_id, range_start=None, range_length=None, insert_before=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def delete_playlist_tracks(self, playlist_id, track_uris, **kwargs):
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
        return (await self._send_authorized_request(kwargs['r'])).json

##### Tracks

    @_prep_request
    async def user_tracks(self, market=None, limit=None, offset=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def tracks(self, track_ids, market=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def _track(self, track_id, market=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def owns_tracks(self, track_ids, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def save_tracks(self, track_ids, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def delete_tracks(self, track_ids, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

##### Artists

    @_prep_request
    async def artists(self, artist_ids, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def _artist(self, artist_id, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def followed_artists(self, after=None, limit=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def follows_artists(self, artist_ids, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def follow_artists(self, artist_ids, **kwargs):       
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def unfollow_artists(self, artist_ids, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def artist_related_artists(self, artist_id, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def artist_top_tracks(self, artist_id, country=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

##### Albums

    @_prep_request
    async def albums(self, album_ids, market=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def _album(self, album_id, market=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def user_albums(self, limit=None, offset=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def owns_albums(self, album_ids, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def save_albums(self, album_ids, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def delete_albums(self, album_ids, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

##### Users

    @property
    async def me(self):
        res = (await self._send_authorized_request(super(self.__class__, self)._prep_me())).json

    @property
    async def is_premium(self):
        res = (await self._send_authorized_request(super(self.__class__, self)._prep_is_premium())).json

    @_prep_request
    async def user_profile(self, user_id, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def follows_users(self, user_ids, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def follow_users(self, user_ids, **kwargs):       
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def unfollow_users(self, user_ids, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

##### Others

    @_prep_request
    async def album_tracks(self, album_id, market=None, limit=None, offset=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def artist_albums(self, artist_id, include_groups=None, market=None, limit=None, offset=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def user_top_tracks(self, time_range=None, limit=None, offset=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def user_top_artists(self, time_range=None, limit=None, offset=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_nullable_response
    @_prep_request
    async def next_page(self, response=None, url=None, **kwargs):
        '''
        You can provide either a response dict or a url
        Providing a URL will be slightly faster as Pyfy will not have to search for the key in the response dict
        '''
        if kwargs['r'] is not None:
            return (await self._send_authorized_request(kwargs['r'])).json
        await asyncio.sleep(0)  # To remove the "never awaited" warning
        return {}

    @_nullable_response
    @_prep_request
    async def previous_page(self, response=None, url=None, **kwargs):
        '''
        You can provide either a response dict or a url
        Providing a URL will be slightly faster as Pyfy will not have to search for the key in the response dict
        '''
        if kwargs['r'] is not None:
            return (await self._send_authorized_request(kwargs['r'])).json
        await asyncio.sleep(0)  # To remove the "never awaited" warning
        return {}


##### Personalization & Explore

    @_prep_request
    async def category(self, category_id, country=None, locale=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def categories(self, country=None, locale=None, limit=None, offset=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def category_playlist(self, category_id, country=None, limit=None, offset=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def available_genre_seeds(self, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def featured_playlists(self, country=None, locale=None, timestamp=None, limit=None, offset=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def new_releases(self, country=None, limit=None, offset=None, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def search(self, q, types='track', market=None, limit=None, offset=None, **kwargs):
        ''' 'track' or ['track'] or 'artist' or ['track','artist'] '''
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def track_audio_analysis(self, track_id, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def _track_audio_features(self, track_id, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
    async def tracks_audio_features(self, track_ids, **kwargs):
        return (await self._send_authorized_request(kwargs['r'])).json

    @_prep_request
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
        **kwargs
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
        return (await self._send_authorized_request(kwargs['r'])).json
