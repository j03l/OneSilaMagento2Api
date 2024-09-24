from __future__ import annotations
from typing import Union, Optional, TYPE_CHECKING, Dict
import requests

if TYPE_CHECKING:
    from . import Client


class MagentoError(Exception):

    """Base exception class for error responses returned by the Magento API

    :cvar DEFAULT_MSG: default exception message to use if a message isn't provided
    """

    DEFAULT_MSG = 'An error occurred while processing the request.'

    def __init__(self, client: Client, msg: Optional[str] = None, response: Optional[requests.Response] = None):
        """Log and raise a MagentoError

        :param client: an initialized :class:`~.Client` object
        :param msg: optional exception message; prepended to the error message of the response
        :param response: optional response to :meth:`parse` an error message from
        """
        self.message = msg if msg else self.DEFAULT_MSG
        self.logger = client.logger

        if response is not None:
            self.message += '\n' + self.parse(response)

        self.logger.error(self.message)
        super().__init__(self.message)

    @staticmethod
    def parse(response: Union[requests.Response, Dict]) -> str:
        """Parses the error message from the ``response``

        :param response: a bad response returned by the Magento API
        :raises: TypeError if ``response`` is not a :class:`~requests.Response` or :class:`Dict`
        """
        if isinstance(response, requests.Response):
            response = response.json()
        elif not isinstance(response, Dict):
            raise TypeError(f"`response` must be a `dict` or {requests.Response}")

        message = response.get('message', '')
        params = response.get('parameters')
        errors = response.get('errors')

        if message:
            message = f'Message: "{message}"'

        if errors:
            for error in errors:
                err_msg = error['message']
                err_params = error.get('parameters')

                if err_params:
                    for param in err_params:
                        err_msg = err_msg.replace(f'%{param}', f'{err_params[param]}')

                message += '\n' + err_msg

        if params:
            if isinstance(params, dict):
                for param in params:  # Same format as error params
                    message = message.replace(f'%{param}', f'{params[param]}')

            elif isinstance(params, list):  # List of param values
                for i, param in enumerate(params, 1):  # Message has params as %{index}, starting from 1
                    message = message.replace(f'%{i}', param)

        return message


class AuthenticationError(MagentoError):

    """Exception class for errors when trying to :meth:`~.authenticate` a :class:`~.Client`"""

    DEFAULT_MSG = 'Failed to authenticate credentials.'

    def __init__(self, client: Client, msg: Optional[str] = None, response: Optional[requests.Response] = None):
        super().__init__(client, msg, response)

class OperationNotAllowedError(MagentoError):
    """Exception class for when an operation is not allowed on a model"""

    def __init__(self, client: Client, method: str, model: str, response: Optional[requests.Response] = None):
        """
        Initialize the exception with the method and model details.

        :param client: an initialized :class:`~.Client` object
        :param method: the method that is not allowed (e.g., 'CREATE', 'UPDATE')
        :param model: the name of the model on which the method is not allowed
        :param response: optional response to parse an error message from
        """
        msg = f'Method "{method}" is not allowed for model "{model}".'
        super().__init__(client, msg, response)

class InstanceGetFailed(Exception):
    """Raised when the creation of a model instance fails."""
    def __init__(self, message):
        super().__init__(message)

class InstanceCreateFailed(Exception):
    """Raised when the creation of a model instance fails."""
    def __init__(self, message):
        super().__init__(message)

class InstanceUpdateFailed(Exception):
    """Raised when the creation of a model instance fails."""
    def __init__(self, message):
        super().__init__(message)

class InstanceDeleteFailed(Exception):
    """Raised when an instance deletion operation fails."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class LockedAttributeError(Exception):
    """Raised when an attribute is locked and cannot be modified or deleted."""
    pass

class GeneralApiError(Exception):
    """Raised for general API errors."""
    pass


class GroupNotFoundError(Exception):
    """Custom exception raised when a group is not found."""

    def __init__(self, group_name: str):
        super().__init__(f"Attribute group '{group_name}' does not exist.")
        self.group_name = group_name