import pprint
import logging

logger = logging.getLogger(__name__)


class SpotifyError(Exception):
    """
    Base error class for ApiError and AuthError
    """

    def _build_super_msg(self, msg, http_res, http_req, e):
        if not http_req and not http_res and not e:
            return msg
        elif (
            getattr(http_res, "status_code", None) == 400 and http_req
        ):  # If bad request or not found, show url and data
            body = http_req.data or http_req.json
            return "\nError msg: {}\nHTTP Error: 400-Bad request\nRequest URL: {}\nRequest body: {}\nRequest headers: {}".format(
                msg,
                http_req.url,
                pprint.pformat(body),
                pprint.pformat(http_req.headers),
            )
        elif getattr(http_res, "status_code", None) == 401 and http_req:
            return "\nError msg: {}\nHTTP Error: {}.\nRequest headers: {}".format(
                msg, http_res.status_code, pprint.pformat(http_req.headers)
            )
        elif getattr(http_res, "status_code", None) == 403 and http_req:
            body = http_req.data or http_req.json
            return "\nError msg: {}\nHTTP Error: 403-Forbidden\nRequest URL: {}\nRequest body: {}\nRequest headers: {}".format(
                msg,
                http_req.url,
                pprint.pformat(body),
                pprint.pformat(http_req.headers),
            )
        elif getattr(http_res, "status_code", None) == 404 and http_req:
            body = http_req.data or http_req.json
            return "\nError msg: {}\nHTTP Error: 404-Resource not found\nRequest URL: {}\nRequest body: {}".format(
                msg, http_req.url, pprint.pformat(body)
            )
        return pprint.pformat(
            {
                "msg": msg,
                "http_response": http_res.__dict__,
                "http_request": http_req.__dict__,
                "original exception": e,
            }
        )


class ApiError(SpotifyError):
    """ 
    Almost any HTTP error other that 401 raises this error
    https://developer.spotify.com/documentation/web-api/#response-schema // regular error object 
    
    Attributes:

        msg (str): Error msg returned from Spotify
        http_response: Full HTTP response
        http_request: Full HTTP request that caused this error
        code (int): HTTP status code
    """

    def __init__(self, msg, http_response=None, http_request=None, e=None):
        self.msg = msg
        self.http_response = http_response
        self.http_request = http_request
        self.code = getattr(http_response, "status_code", None)
        super_msg = self._build_super_msg(msg, http_response, http_request, e)
        logger.error(super_msg)
        super(ApiError, self).__init__(super_msg)


class AuthError(SpotifyError):
    """ Raised when a 401 or any Authentication error is encountered
    https://developer.spotify.com/documentation/web-api/#response-schema // authentication error object 
    
    Attributes:

        msg (str): Error msg returned from Spotify
        http_response: Full HTTP response
        http_request: Full HTTP request that caused this error
        code (int): HTTP status code
    """

    def __init__(self, msg, http_response=None, http_request=None, e=None):
        self.msg = msg
        self.http_response = http_response
        self.http_request = http_request
        self.code = getattr(http_response, "status_code", None)
        super_msg = self._build_super_msg(msg, http_response, http_request, e)
        logger.error(super_msg)
        super(AuthError, self).__init__(super_msg)


class _TooManyRequests(ApiError):
    pass
