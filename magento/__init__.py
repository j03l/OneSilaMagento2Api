from . import clients
from . import managers
from . import models
from . import utils
from . import exceptions
import os

__version__ = "1.0.6"

from .constants import AuthenticationMethod

Client = clients.Client
logger = utils.MagentoLogger(
    name=utils.MagentoLogger.PACKAGE_LOG_NAME,
    log_file=utils.MagentoLogger.PACKAGE_LOG_NAME + '.log',
    stdout_level='WARNING'  # Clients will log to console
)


def get_api(**kwargs) -> Client:
    """Initialize a :class:`~.Client` using credentials stored in environment variables

    Any valid :class:`~.Client` kwargs can be used in addition to and/or instead of environment variables

    **Usage**::

      import magento

      api = magento.get_api()

    :param kwargs: any valid kwargs for :class:`~.Client`
    :raises ValueError: if login credentials are missing
    """
    credentials = {
        'domain': kwargs.get('domain', os.getenv('MAGENTO_DOMAIN')),
        'username': kwargs.get('username', os.getenv('MAGENTO_USERNAME')),
        'password': kwargs.get('password', os.getenv('MAGENTO_PASSWORD')),
        'api_key': kwargs.get('api_key', os.getenv('MAGENTO_API_KEY')),
        'authentication_method': kwargs.get('authentication_method', AuthenticationMethod.PASSWORD.value),
        'local': kwargs.get('local', False),
    }

    # Check if domain is provided, which is mandatory
    if credentials['domain'] is None:
        raise ValueError("Missing login credentials: 'domain' is required.")

    # Check the combination of credentials based on the authentication method
    if credentials['authentication_method'] == AuthenticationMethod.PASSWORD.value:
        if credentials['username'] is None or credentials['password'] is None:
            raise ValueError("Missing login credentials: 'username' and 'password' are required for PASSWORD authentication.")

    elif credentials['authentication_method'] == AuthenticationMethod.TOKEN.value:
        if credentials['api_key'] is None:
            raise ValueError("Missing login credentials: 'api_key' is required for TOKEN authentication.")

    else:
        raise ValueError(f"Unsupported authentication method: {credentials['authentication_method']}")

    # Return the initialized Client
    return Client.from_dict(credentials)


logger.debug('Initialized MyMagento')
