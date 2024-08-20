from json import JSONDecodeError
from functools import wraps
from time import sleep

from magento.constants import ModelMethod


def jsondecode_error_retry(tries=4, delay=3, backoff=2):
    """Retry calling the decorated function using an exponential backoff.

    This is needed because the magento-api often returns a 502-bad gateway-error.
    We don't really test the status-code in a proper way - here we're just tyring
    to test the json response.  If it returns an error, then grab and retry

    It can also happen that magento returns 2xx code and yet the request failed.
    The only way to discover that it failed is by not having any json available.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    """
    def deco_retry(f):

        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                fn = f(*args, **kwargs)
                try:
                    fn.json()
                    return fn
                except JSONDecodeError as e:
                    msg = "Received JSONDecodeError, Retrying in {} seconds...".format(mdelay)
                    msg += "\nRequest URL: {}".format(fn.request.url)
                    msg += "\nRequest Body: {}".format(fn.request.body)
                    msg += '\nResponse content: \n{}'.format(fn.text)
                    fn.logger.debug(msg)

                    sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff

            return f(*args, **kwargs)

        return f_retry

    return deco_retry


def validate_method_for_model(method: ModelMethod):
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            self.validate_model_method(method)
            return func(self, *args, **kwargs)
        return wrapper
    return decorator

def data_not_fetched_value(get_value):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not self._fetched:
                property_name = f"_{func.__name__}"
                return get_value(self) if hasattr(self, property_name) else None
            return func(self, *args, **kwargs)
        return wrapper
    return decorator



def set_private_attr_after_setter(func):
    @wraps(func)
    def wrapper(self, value, *args, **kwargs):
        # Call the original setter method
        result = func(self, value, *args, **kwargs)

        # Set the private attribute only if value is not None
        if value is not None:
            private_attr_name = f"_{func.__name__}"
            setattr(self, private_attr_name, value)

        return result

    return wrapper