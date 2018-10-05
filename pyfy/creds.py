import os
import json
import socket
import pickle
import datetime
from functools import wraps

from .utils import _create_secret


try:
    DEFAULT_FILENAME_BASE = socket.gethostname() + "_" + "Spotify_"
except:
    DEFAULT_FILENAME_BASE = 'Spotify_'
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


class _Creds:
    def __init__(self, *args, **kwargs):
        raise TypeError('_Creds class isn\'nt calleable')

    def pickle(self, path=os.path.dirname(os.path.abspath(__file__)), name=None):
        if name is None:
            name = DEFAULT_FILENAME_BASE + self.__class__.__name__ + '_pickle'
        path = os.path.join(path, name)
        with open(path, 'wb') as creds_file:
            pickle.dump(self, creds_file, pickle.HIGHEST_PROTOCOL)

    # Unpickling doesn't work by setting an instance's (self) to the output of one of its own methods. Apparently, the method must be external 
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
