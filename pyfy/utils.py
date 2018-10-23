import datetime
import secrets
from urllib import parse
from functools import wraps
from json.decoder import JSONDecodeError
from aiohttp import ContentTypeError
from inspect import iscoroutinefunction
try:
    import ujson as json
except:
    import json

from requests import Response


def _create_secret(bytes_length=32):
    return secrets.base64.standard_b64encode(secrets.token_bytes(bytes_length)).decode('utf-8')


def _safe_getitem(dct, *keys):
    for key in keys:
        try:
            dct = dct[key]
        except (KeyError, TypeError):
            return None
    return dct


def _get_key_recursively(response, key, limit):
    ''' Recursively search for a key in a response 
    Not really sure if that's the most elegant solution.'''
    if response is None:
        raise TypeError('Either provide a response or a URL for the next_page and previous_page methods')

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
            for k , v in dct.items():
                if type(v) == dict:
                    new_stack.append(v)

        # Prepare for next iteration
        stack = new_stack
        iters_performed += 1

    return None  # if iterations don't give back results


def _set_and_get_me_attr_sync(self, attr_name):
    ''' either populates user creds from spotify or just calls self.me and only gets the attr_name passed '''
    # if attribute doesn't exist or if it exists but is set to None, do:
    if (not hasattr(self.user_creds, attr_name)) or (hasattr(self.user_creds, attr_name) and getattr(self.user_creds, attr_name) is None):
        if self._populate_user_creds_ is True:
            self.populate_user_creds()
        else:
            setattr(self.user_creds, attr_name, self.me.get(attr_name))
    return getattr(self.user_creds, attr_name, None)

async def _set_and_get_me_attr_async(self, attr_name):
    ''' either populates user creds from spotify or just calls self.me and only gets the attr_name passed '''
    # if attribute doesn't exist or if it exists but is set to None, do:
    if (not hasattr(self.user_creds, attr_name)) or (hasattr(self.user_creds, attr_name) and getattr(self.user_creds, attr_name) is None):
        if self._populate_user_creds_ is True:
            await self.populate_user_creds()
        else:
            me = await self.me
            setattr(self.user_creds, attr_name, me.get(attr_name))
    return getattr(self.user_creds, attr_name, None)


def _locale_injectable(argument_name, support_from_token=True):  # market or country
    '''
    Injects user's locale if applicable. Only supports one input, either market or country (interchangeable values) 
    I know this isn't the most reusable dependency injector. However, you probably won't need to inject
    any extra locales. Should you need to, feel free to re-implement this decorator.'''
    def outer_wrapper(f):

        @wraps(f)
        def wrapper(self, *args, **kwargs):
            if kwargs.get(argument_name) is None:  # If user didn't assign to the parameter, inject
                if self.default_to_locale is True and self._caller == self.user_creds:  # if caller is a user not client.
                    if support_from_token:  # some endpoints do not support 'from_token' as a country/market parameter.
                        injection = 'from_token'
                    else:
                        injection = _set_and_get_me_attr_sync(self, 'country')
                    kwargs[argument_name] = injection
            try:
                return f(self, *args, **kwargs)
            except TypeError as e:
                raise TypeError('Original exception: {}. Please note: When assigning locales i.e. \'market\' or \'country\'',
                ' to a method, use keyword arguments instead of positional arguments. e.g. market="US" insead of just: "US".'.format(e))
        
        @wraps(f)
        async def async_wrapper(self, *args, **kwargs):
            if kwargs.get(argument_name) is None:  # If user didn't assign to the parameter, inject
                if self.default_to_locale is True and self._caller == self.user_creds:  # if caller is a user not client.
                    if support_from_token:  # some endpoints do not support 'from_token' as a country/market parameter.
                        injection = 'from_token'
                    else:
                        injection = await _set_and_get_me_attr_async(self, 'country')
                    kwargs[argument_name] = injection
            try:
                return await f(self, *args, **kwargs)
            except TypeError as e:
                raise TypeError('Original exception: {}. Please note: When assigning locales i.e. \'market\' or \'country\'',
                ' to a method, use keyword arguments instead of positional arguments. e.g. market="US" insead of just: "US".'.format(e))

        if iscoroutinefunction(f):
            return async_wrapper
        return wrapper

    return outer_wrapper


def _prep_request(f):
    '''
    All this decorator does is that it passes the arguments of the wrapped method to another method
    for some preprocessing and dependency injection.
    The other method should be named '_prep_' + the name of the wrapped method
    e.g. playlists --> _prep_playlists
    The return value of the _prep_ method is then passed on to the original function as the
    keyword argument 'r'.
     '''

    # This decorator should be locked down to not implement any more functionalities as some
    # methods do not use this decorator e.g. `Spotify.me`. Changing it might cause inconsistent results.
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        super_f_name = '_prep_' + f.__name__
        req_method = getattr(super(self.__class__, self), super_f_name)
        req = req_method(*args, **kwargs)
        kwargs['r'] = req
        return f(self, *args, **kwargs)
    
    return wrapper



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
        raise TypeError('Queries must be an instance of a dict and url must be an instance of string in order to be properly encoded')
    safe_query = _safe_query_string(query)
    if safe_query:
        url = url + '?'
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
        return ','.join(list_)
    return list_


def _is_single_resource(resource):
    single_types = [int, str, float]
    if type(resource) in single_types:
        return True
    elif len(resource) == 1:
        return True
    return False


def _convert_to_iso_date(date):
    ''' marked as private as user won't need this for the currently supported endpoints '''
    return date.isoformat()


def convert_from_iso_date(date):
    ''' utility method that can convert dates returned from Spotify's API '''
    if not isinstance(date, datetime.datetime):
        raise TypeError('date must be of type datetime.datetime')
    return datetime.date.fromisoformat(date)

class _Dict(dict):
    def __init__(self, *args, **kwargs):
        super(_Dict, self).__init__(*args, **kwargs)
        for arg in args:
            if isinstance(arg, dict):
                for k, v in arg.items():
                    self[k] = v

        if kwargs:
            for k, v in kwargs.items():
                self[k] = v

    def __getattr__(self, attr):
        return self.get(attr)

    def __setattr__(self, key, value):
        self.__setitem__(key, value)

    def __setitem__(self, key, value):
        super(_Dict, self).__setitem__(key, value)
        self.__dict__.update({key: value})

    def __delattr__(self, item):
        self.__delitem__(item)

    def __delitem__(self, key):
        super(Map, self).__delitem__(key)
        del self.__dict__[key]

def _nullable_response(f):
    ''' wrapper that returns an empty dict instead of a None body. A None body causes json.loads to raise an error '''

    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            original_response = f(*args, **kwargs)
        except JSONDecodeError:
            return {}
        else:
            return original_response

    @wraps(f)
    async def async_wrapper(*args, **kwargs):
        try:
            original_response = await f(*args, **kwargs)
        except ContentTypeError as e:
            return {}
            #if e.request_info == 0:
            #    return {}  # If response is empty return, else raise the error
            #else:
            #    raise e
        else:
            if hasattr(original_response, 'json') is False:
                original_response.json = {}
            if original_response.json is None:
                original_response.json = {}
            return original_response

    if iscoroutinefunction(f):
        return async_wrapper
    return wrapper

@_nullable_response
async def _resolve_async_response(res):
    ''' Function to convert and resolve future responses from aiohttp for more stable error handling '''
    full_res = _Dict()
    keys_and_attrs = [(key, getattr(res, key)) for key in dir(res) if not key.startswith('_')]
    async with res:
        for key, attr in keys_and_attrs:
            # NOTE: It is not possible to use read(), json() or text() after explicit reading from content.
            if iscoroutinefunction(attr):
                if key == 'json':
                    setattr(full_res, key, await attr(loads=json.loads))  # awaits aiohttp.ClientResponse.json()
            else:
                if key == 'status':
                    setattr(full_res,  'status_code', attr)
                else:
                    setattr(full_res, key, attr)
    return full_res

@_nullable_response
def _resolve_response(res):
    ''' Function to convert and resolve future responses from aiohttp for more stable error handling '''
    awaited_res = _Dict()
    keys_and_attrs = [(key, getattr(res, key)) for key in dir(res) if not key.startswith('_')]
    for key, attr in keys_and_attrs:
        if iscoroutinefunction(attr):
            continue
        else:
            if key == 'status':
                setattr(awaited_res,  'status_code', attr)
            else:
                setattr(awaited_res, key, attr)
    return awaited_res
