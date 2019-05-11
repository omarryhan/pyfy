from functools import wraps
from inspect import iscoroutinefunction

from json.decoder import JSONDecodeError


def _set_and_get_me_attr_sync(self, attr_name):
    """ either populates user creds from spotify or just calls self.me and gets (and sets) the attr_name passed """
    # if attribute doesn't exist or if it exists but is set to None, do:
    if (not hasattr(self.user_creds, attr_name)) or (
        hasattr(self.user_creds, attr_name)
        and getattr(self.user_creds, attr_name) is None
    ):
        if self._populate_user_creds_ is True:
            self.populate_user_creds()
        else:
            setattr(self.user_creds, attr_name, self.me().get(attr_name))
    return getattr(self.user_creds, attr_name, None)


async def _set_and_get_me_attr_async(self, attr_name):
    """ either populates user creds from spotify or just calls self.me() and only gets the attr_name passed """
    # if attribute doesn't exist or if it exists but is set to None, do:
    if (not hasattr(self.user_creds, attr_name)) or (
        hasattr(self.user_creds, attr_name)
        and getattr(self.user_creds, attr_name) is None
    ):
        if self._populate_user_creds_ is True:
            await self.populate_user_creds()
        else:
            me = await self.me()
            setattr(self.user_creds, attr_name, me.get(attr_name))
    return getattr(self.user_creds, attr_name, None)


def _default_to_locale(argument_name, support_from_token=True):  # market or country
    """
    Injects user's locale if applicable. Only supports one input, either market or country (interchangeable values) 
    I know this isn't the most reusable dependency injector. However, you probably won't need to inject
    any extra locales. Should you need to, feel free to re-implement this decorator."""

    def outer_wrapper(f):
        @wraps(f)
        def wrapper(self, *args, **kwargs):
            if (
                kwargs.get(argument_name) is None
            ):  # If user didn't assign to the parameter, inject
                if (
                    self.default_to_locale is True and self._caller == self.user_creds
                ):  # if caller is a user not client.
                    if (
                        support_from_token
                    ):  # some endpoints do not support 'from_token' as a country/market parameter.
                        injection = "from_token"
                    else:
                        injection = _set_and_get_me_attr_sync(self, "country")
                    kwargs[argument_name] = injection
            try:
                return f(self, *args, **kwargs)
            except TypeError as e:
                raise TypeError(
                    f"Original exception: {e}.\n\nPlease note: When assigning locales i.e. 'market' or 'country'"
                    ' to a method, use keyword arguments instead of positional arguments. e.g. market="US" insead of just: "US".'
                )

        @wraps(f)
        async def async_wrapper(self, *args, **kwargs):
            if (
                kwargs.get(argument_name) is None
            ):  # If user didn't assign to the parameter, inject
                if (
                    self.default_to_locale is True and self._caller == self.user_creds
                ):  # if caller is a user not client.
                    if (
                        support_from_token
                    ):  # some endpoints do not support 'from_token' as a country/market parameter.
                        injection = "from_token"
                    else:
                        injection = await _set_and_get_me_attr_async(self, "country")
                    kwargs[argument_name] = injection
            try:
                return await f(self, *args, **kwargs)
            except TypeError as e:
                raise TypeError(
                    f"Original exception: {e}.\n\nPlease note: When assigning locales i.e. 'market' or 'country'"
                    ' to a method, use keyword arguments instead of positional arguments. e.g. market="US" insead of just: "US".'
                )

        if iscoroutinefunction(f):
            return async_wrapper
        return wrapper

    return outer_wrapper


def _inject_user_id(f):
    """ Injects user_id if not found in kwargs. The name of the injection should be kwarg['user_id'] """

    @wraps(f)
    def wrapper(self, *args, **kwargs):
        if kwargs.get("user_ids") is None and kwargs.get("user_id") is None:
            user_id = _set_and_get_me_attr_sync(self, "id")
            kwargs["user_id"] = user_id
        return f(self, *args, **kwargs)

    @wraps(f)
    async def async_wrapper(self, *args, **kwargs):
        if kwargs.get("user_ids") is None and kwargs.get("user_id") is None:
            user_id = await _set_and_get_me_attr_async(self, "id")
            kwargs["user_id"] = user_id
        return await f(self, *args, **kwargs)

    if iscoroutinefunction(f):
        return async_wrapper
    return wrapper


def _dispatch_request(*_args, authorized_request=True):
    """ 
    1. Preps request after all argument injections have been injected
    2. Returns the request if to_gather was specified
    3. Defaults to sending an authorized request
    4. if authorized_request is False it, will send an request without the default authorization headers
    """

    def outer_wrapper(f):
        @wraps(f)
        def sync_wrapper(self, *args, **kwargs):
            args_with_injections, kwargs_with_injections = f(self, *args, **kwargs)
            request_factory = getattr(
                super(self.__class__, self), ("_prep_" + f.__name__)
            )
            request = request_factory(*args_with_injections, **kwargs_with_injections)

            if kwargs.get("to_gather") is True:
                return request

            else:
                if request is not None:  # compat for next_page and prev_page
                    try:
                        if authorized_request is True:
                            return self._send_authorized_request(request).json()
                        else:
                            return self._send_request(request).json()
                    except JSONDecodeError:
                        return {}
                else:
                    return {}

        @wraps(f)
        async def async_wrapper(self, *args, **kwargs):
            args_with_injections, kwargs_with_injections = await f(
                self, *args, **kwargs
            )
            request_factory = getattr(
                super(self.__class__, self), ("_prep_" + f.__name__)
            )
            request = request_factory(*args_with_injections, **kwargs_with_injections)

            if kwargs.get("to_gather") is True:
                return request

            else:
                if request is not None:  # compat for next_page and prev_page
                    if authorized_request is True:
                        return (await self._send_authorized_requests(request)).json
                    else:
                        return (await self._send_requests(request)).json
                else:
                    return {}

        if iscoroutinefunction(f):
            return async_wrapper
        else:
            return sync_wrapper

    # Makes your wrapped function without necessarily passing args.
    # Where _*args is an optional `f` (wrapped function).
    if _args:
        return outer_wrapper(*_args)
    else:
        return outer_wrapper
