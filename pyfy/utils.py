import datetime
import warnings
import secrets
from urllib import parse

try:
    import ujson as json
except:
    import json


def _create_secret(bytes_length=32):  # pragma: no cover
    return secrets.base64.standard_b64encode(secrets.token_bytes(bytes_length)).decode(
        "utf-8"
    )


def _safe_getitem(dct, *keys):
    for key in keys:
        try:
            dct = dct[key]
        except (KeyError, TypeError):
            return None
    return dct


def _get_key_recursively(response, key, limit):
    """ Recursively search for a key in a response 
    Not really sure if that's the most elegant solution."""
    if response is None:
        raise TypeError(
            "Either provide a response or a URL for the next_page and previous_page methods"
        )

    stack = [response]
    iters_performed = 0
    while iters_performed < limit and len(stack) > 0:
        # Check if dicts have the key in their top layer, if yes, return
        for dct in stack:
            key_found = dct.get(key)
            if key_found is not None:
                return key_found

        # If not in current stack make a new stack with the second layer of each dict in the original stack
        new_stack = []
        for dct in stack:
            for k, v in dct.items():
                if type(v) == dict:
                    new_stack.append(v)

        # Prepare for next iteration
        stack = new_stack
        iters_performed += 1

    return None  # if iterations don't give back results


def _safe_query_string(query):
    bad_types = [None, tuple(), dict(), list()]
    safe_query = {}
    for k, v in query.items():
        if v not in bad_types:
            if type(v) == bool:
                v = json.dumps(v)
            safe_query[k] = v
    return safe_query


def _build_full_url(url, query):
    if not isinstance(query, dict) or not isinstance(url, str):
        raise TypeError(
            "Queries must be an instance of a dict and url must be an instance of string in order to be properly encoded"
        )
    safe_query = _safe_query_string(query)
    if safe_query:
        url = url + "?"
    return url + parse.urlencode(safe_query)


def _safe_json_dict(data):
    safe_types = [float, str, int, bool]
    safe_json = {}
    for k, v in data.items():
        if type(v) in safe_types:
            safe_json[k] = v
        elif type(v) == dict and len(v) > 0:
            safe_json[k] = _safe_json_dict(v)
    return safe_json


def _comma_join_list(list_):
    if type(list_) == list:
        return ",".join(list_)
    return list_


def _is_single_resource(resource):
    single_types = [int, str, float]
    if type(resource) in single_types:
        return True
    elif len(resource) == 1:
        return True
    return False


def _convert_to_iso_date(date):  # pragma: no cover
    """ marked as private as user won't need this for the currently supported endpoints """
    return date.isoformat()


def convert_from_iso_date(date):  # pragma: no cover
    """ utility method that can convert dates returned from Spotify's API """
    return datetime.date.fromisoformat(date)


class _Dict(dict):  # pragma: no cover
    def __init__(self, *args, **kwargs):  # pragma: no cover
        super(_Dict, self).__init__(*args, **kwargs)
        for arg in args:
            if isinstance(arg, dict):
                for k, v in arg.items():
                    self[k] = v

        if kwargs:
            for k, v in kwargs.items():
                self[k] = v

    def __getattr__(self, attr):  # pragma: no cover
        return self.get(attr)

    def __setattr__(self, key, value):  # pragma: no cover
        self.__setitem__(key, value)

    def __setitem__(self, key, value):  # pragma: no cover
        super(_Dict, self).__setitem__(key, value)
        self.__dict__.update({key: value})

    def __delattr__(self, item):  # pragma: no cover
        self.__delitem__(item)

    def __delitem__(self, key):  # pragma: no cover
        super(_Dict, self).__delitem__(key)
        del self.__dict__[key]
