import os
import sys
import warnings

try:
    import ujson as json
except:
    import json
import socket
import pickle
import datetime
from functools import wraps

from .utils import _create_secret


try:
    DEFAULT_FILENAME_BASE = socket.gethostname() + "_" + "Spotify_"
except:
    DEFAULT_FILENAME_BASE = "Spotify_"

ALL_SCOPES = [
    "streaming",  # Playback
    "app-remote-control",
    "user-follow-modify",  # Follow
    "user-follow-read",
    "playlist-read-private",  # Playlists
    "playlist-modify-private",
    "playlist-read-collaborative",
    "playlist-modify-public",
    "user-modify-playback-state",  # Spotify Connect
    "user-read-playback-state",
    "user-read-currently-playing",
    "user-read-private",  # Users
    "user-read-birthdate",
    "user-read-email",
    "user-library-read",  # Library
    "user-library-modify",
    "user-top-read",  # Listening History
    "user-read-recently-played",
]
""" List of all scopes provided by Spotify """


class _Creds:
    def __init__(self, *args, **kwargs):
        raise TypeError("_Creds class shouldn'nt initiate attrs")

    def pickle(self, path=None, name=None):
        """
        Pickles Credentials

        Arguments:

            path (str): path of the directory to store pickle in

            name (str): name of the file.
        """
        if path is None:
            path = os.path.dirname(os.path.abspath(__file__))
        if name is None:
            name = DEFAULT_FILENAME_BASE + self.__class__.__name__ + "_pickle"
        path = os.path.join(path, name)
        with open(path, "wb") as creds_file:
            pickle.dump(self, creds_file, pickle.HIGHEST_PROTOCOL)

    @classmethod
    def unpickle(cls, path=None, name=None):
        """
        Loads a Credentials Pickle from file

        Arguments:

            path (str): path of the directory you want to unpickle from

            name (str): name of the file.
        """
        if path is None:
            path = os.path.dirname(os.path.abspath(__file__))
        if name is None:
            name = DEFAULT_FILENAME_BASE + cls.__name__ + "_pickle"
        path = os.path.join(path, name)
        with open(path, "rb") as creds_file:
            return pickle.load(creds_file)

    def _delete_pickle(
        self, path=os.path.dirname(os.path.abspath(__file__)), name=None
    ):
        """ BE CAREFUL!! THIS WILL PERMENANTLY DELETE ONE OF YOUR FILES IF USED INCORRECTLY
            It is recommended you leave the defaults if you're using this library for personal use only """
        if name is None:
            name = DEFAULT_FILENAME_BASE + self.__class__.__name__ + "_pickle"
        path = os.path.join(path, name)
        os.remove(path)

    def save_as_json(self, path=None, name=None):
        """
        Saves credentials as a json file

        Arguments:

            path (str): path of the directory you want to save the file in

            name (str): name of the file.
        """
        if path is None:
            path = os.path.dirname(os.path.abspath(__file__))
        if name is None:
            name = DEFAULT_FILENAME_BASE + self.__class__.__name__ + ".json"
        path = os.path.join(path, name)
        with open(path, "w") as outfile:
            if "ujson" in sys.modules:
                json.dump(self.__dict__, outfile)
            else:
                json.dump(self.__dict__, outfile, default=str)

    def load_from_json(self, path=None, name=None):
        """
        Loads credentials from JSON file

        Arguments:

            path (str): path of the directory the file is located in

            name (str): name of the file.
        """
        if path is None:
            path = os.path.dirname(os.path.abspath(__file__))
        if name is None:
            name = DEFAULT_FILENAME_BASE + self.__class__.__name__ + ".json"
        path = os.path.join(path, name)
        with open(path, "r") as infile:
            self.__dict__.update(json.load(infile))

    def _delete_json(self, path=os.path.dirname(os.path.abspath(__file__)), name=None):
        if name is None:
            name = DEFAULT_FILENAME_BASE + self.__class__.__name__ + ".json"
        path = os.path.join(path, name)
        os.remove(path)

    @property
    def access_is_expired(self):
        """
        Returns:

            bool: Whether access token expired or not
        """
        if isinstance(self.expiry, datetime.datetime):
            return self.expiry <= datetime.datetime.utcnow()
        return None

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except AttributeError as e:
            raise KeyError(e)

    def get(self, key):
        return getattr(self, key, None)

    def __setitem__(self, key, value):
        setattr(self, key, value)


class ClientCreds(_Creds):
    """
    OAuth2 Client Credentials
    
    Arguments:

        client_id (str): OAuth2 client_id

        client_secret (str): OAuth2 client_secret

        scopes (list): OAuth2 scopes. Defaults to all scopes

        redirect_uri (str): OAuth2 redirect uri. Defaults to http://localhost

        show_dialog (bool): if set to false, Spotify will not show a new authentication request if user already authorized the client
    """

    def __init__(
        self,
        client_id=None,
        client_secret=None,
        scopes=None,
        redirect_uri=None,
        show_dialog=False,
    ):
        if redirect_uri is None:
            redirect_uri = "http://localhost"
        if scopes is None:
            scopes = ALL_SCOPES
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes
        self.redirect_uri = redirect_uri
        self.show_dialog = show_dialog

        self.access_token = None  # For client credentials oauth flow
        self.expiry = None  # For client credentials oauth flow

    def load_from_env(self):
        """
        Load client creds from OS environment

        SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET and SPOTiFY_REDIRECT_URI environment variables must be present
        """
        self.client_id = os.environ["SPOTIFY_CLIENT_ID"]
        self.client_secret = os.environ["SPOTIFY_CLIENT_SECRET"]
        self.redirect_uri = os.environ["SPOTIFY_REDIRECT_URI"]

    @property
    def is_oauth_ready(self):
        if (
            self.client_id
            and self.redirect_uri
            and self.scopes
            and self.show_dialog is not None
        ):
            return True
        return False


class UserCreds(_Creds):
    """
    OAuth2 User Credentials + Spotify's User info

    Note:

        For convenience, if you set the populate_user_creds flag to True in any of Pyfy's clients, this will set all of Spotify's basic information on user to this model

    Arguments:

        access_token (str): OAuth2 access token

        refresh_token (str): OAuth2 refresh token

        scopes (list): OAuth2 scopes

        expiry (datetime.datetime): Datetime access token expires

        user_id (str): Not to be confused with OpenID, this is the user's Spotify ID

    Attributes:
        
        birthdate (str):  From Spotify's /me endpoint
        
        country (str):  From Spotify's /me endpoint
        
        display_name (str):  From Spotify's /me endpoint
        
        email (str):  From Spotify's /me endpoint
        
        external_urls (dict):  From Spotify's /me endpoint
        
        followers (dict):  From Spotify's /me endpoint
        
        href (str):  From Spotify's /me endpoint
        
        id (str):  From Spotify's /me endpoint
        
        images (list):  From Spotify's /me endpoint
        
        product (str):  From Spotify's /me endpoint
        
        type (str):  From Spotify's /me endpoint
        
        uri (str): From Spotify's /me endpoint
    """

    def __init__(
        self,
        access_token=None,
        refresh_token=None,
        scopes=None,
        expiry=None,
        user_id=None,
        state=None,
    ):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expiry = expiry  # expiry date. Not to be confused with expires in
        self.user_id = user_id
        if state is not None:
            warnings.warn(
                "user_creds.state is deprecated and will soon be removed",
                DeprecationWarning,
            )
        self.state = state
        self.country = None
        self.scopes = scopes or []

        # Spotify's user info
        self.birthdate = None
        self.country = None
        self.display_name = None
        self.email = None
        self.external_urls = None
        self.followers = None
        self.href = None
        self.id = None
        self.images = None
        self.product = None
        self.type = None
        self.uri = None

    def load_from_env(self):
        """
        Load user creds from env

        SPOTIFY_ACCESS_TOKEN and SPOTIFY_REFRESH_TOKEN environment variables must be present

        This method will not fail if it didn't find a refresh token, but will fail if no access token was found
        """
        self.access_token = os.environ["SPOTIFY_ACCESS_TOKEN"]
        self.refresh_token = os.getenv("SPOTIFY_REFRESH_TOKEN", None)


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
