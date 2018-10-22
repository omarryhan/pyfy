from .client import ClientCreds, UserCreds, Spotify, AuthError, ApiError, SpotifyError, ALL_SCOPES


__name__ = 'pyfy'
__about__ = "Lightweight python wrapper for Spotify's web API"
__url__ = 'https://github.com/omarryhan/pyfy'
__version_info__ = ('0', '0', '13')
__version__ = '.'.join(__version_info__)
__author__ = 'Omar Ryhan'
__author_email__ = 'omarryhan@gmail.com'
__maintainer__ = 'Omar Ryhan'
__license__ = 'MIT'
__copyright__ = '(c) 2018 by Omar Ryhan'
__all__ = [
    'SpotifyError',
    'ApiError',
    'AuthError',
    'ClientCreds',
    'UserCreds',
    'Spotify'
]