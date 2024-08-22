from __future__ import annotations
from functools import cached_property
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Union, Optional, List, Dict
from magento import clients
import urllib.parse
import inspect
from ..constants import ModelMethod
from ..decorators import validate_method_for_model
from ..exceptions import OperationNotAllowedError, MagentoError, InstanceDeleteFailed, InstanceUpdateFailed, InstanceGetFailed
from ..utils import get_payload_prefix

if TYPE_CHECKING:
    from magento.managers import Manager


class Model(ABC):

    """The abstract base class of all API response wrapper classes

    **Overview**

    * A :class:`Model` wraps the response ``data`` from an API ``endpoint``
    * Several endpoints have subclasses with additional methods to retrieve/update/create data
    * All other endpoints are wrapped using a general :class:`~.APIResponse`
    * The endpoint's corresponding :class:`~.Manager` can be accessed via :meth:`~.query_endpoint`
    """

    DOCUMENTATION: str = None  #: Link to the Official Magento 2 API documentation for the endpoint wrapped by the Model
    IDENTIFIER: str = None  #: The API response field that the endpoint's :attr:`~.Model.uid` comes from
    ALLOWED_METHODS = [ModelMethod.GET] # get is the default method. But we can customize models to allow certain model methods
    PAYLOAD_PREFIX = None # the key of the payload where the data goes. If missing we will use utils.get_payload_prefix to get it

    def __init__(self, data: dict,
                 client: clients.Client,
                 endpoint: str,
                 fetched: bool = False,
                 list_endpoint: Optional[str] = None
                 ):
        """Initialize a :class:`Model` object from an API response and the ``endpoint`` that it came from

        ...

        .. tip:: The ``endpoint`` is used to:

           * Generate the :meth:`~.url_for` any requests made by subclass-specific methods
           * Match the :class:`~.Model` to its corresponding :class:`~.Manager` object
           * Determine how to :meth:`~.Model.parse` new :class:`~.Model` objects from API responses

        ...

        :param data: the JSON from an API response to use as source data
        :param client: an initialized :class:`~.Client`
        :param endpoint: the API endpoint that the :class:`Model` wraps
        :param private_keys: if ``True``, sets the keys in the :attr:`~.excluded_keys` as private attributes
        :param fetched: True means it's from the API (existent data) False means it's initialized (about to be created)
            (prefixed with ``__``) instead of fully excluding them

        """
        if not isinstance(data, dict):
            raise TypeError(f'Parameter "data" must be of type {dict}')
        if not isinstance(endpoint, str):
            raise TypeError(f'Parameter "endpoint" must be of type {str}')
        if not isinstance(client, clients.Client):
            raise TypeError(f'Parameter "client" must be of type {clients.Client}')

        # Initialize mutable_data as an empty dictionary
        # For the models that allows update / create this is the data that can be initialized and changed
        self.mutable_data = {}
        self.mutable_initial_values = {}

        self.data = data
        self._fetched = fetched
        self.client = client
        self.endpoint = endpoint
        self.logger = client.logger
        self.set_attrs(data)

        # most of the models have the same endpoint for the list but some as attribute sets have another endpoint
        self.list_endpoint = list_endpoint if list_endpoint is not None else endpoint

    def set_attrs(self, data: dict) -> None:
        """Initializes object attributes using the JSON from an API response as the data source

        Called at the time of object initialization, but can also be used to update the source data and
        reinitialize the attributes without creating a new object

        :param data: the API response JSON to use as the object source data

        .. admonition:: **Private Keys Clarification**
           :class: info

           Let's say that ``"status"`` is in the :attr:`~.excluded_keys`

           * No matter what, the ``status`` attribute will not be set on the :class:`Model`
        """

        private_keys = len(self.excluded_keys)
        missing_keys = set(self.required_keys) - set(data)

        if isinstance(self, APIResponse):
            missing_keys = []

        if missing_keys:
            raise ValueError(f'Missing required keys in data: {", ".join(missing_keys)}')

        keys = set(data) - set(self.excluded_keys)
        class_properties = [name for name, obj in inspect.getmembers(self.__class__) if isinstance(obj, property)]

        for key in keys:
            value = None
            if key == 'custom_attributes':
                if attrs := data[key]:
                    value = self.unpack_attributes(attrs)

                    # Store the packed attributes in mutable_initial_values
                    # @TODO: Think of a better way to do this! Maybe not in the Model but in the Product
                    # or convert this whole if from key == 'custom_attributes' where we can unpack things based on a config but still get the mutable
                    # mutable_initial_values
                    for attr in attrs:
                        if attr['attribute_code'] in self.mutable_keys:
                            self.mutable_initial_values[attr['attribute_code']] = {
                                'attribute_code': attr['attribute_code'],
                                'value': attr['value']
                            }
            else:
                value = data[key]

            # Check if the key corresponds to a property
            # Use the prefixed underscore
            if key in class_properties:
                setattr(self, '_' + key, value)

            setattr(self, key, value)
            if key in self.mutable_keys:
                self.mutable_initial_values[key] = value

        if private_keys:
            private = '_' + self.__class__.__name__ + '__'
            for key in self.excluded_keys:
                setattr(self, private + key, data.get(key))

        self.data = data

    @property
    def excluded_keys(self) -> List[str]:
        """API response keys that shouldn't be set as object attributes by :meth:`~.set_attrs`

        :returns: list of API response keys that shouldn't be set as attributes
        """
        return []

    @property
    def required_keys(self) -> List[str]:
        """API response keys that must be present in the data

        :returns: list of API response keys that must be present
        """
        return []

    @property
    def mutable_keys(self) -> List[str]:
        """API response keys that can be modified after initialization

        :returns: list of API response keys that are mutable
        """
        return []

    @property
    def required_for_update_keys(self) -> List[str]:
        """API response keys that are required for a payload but not updatable
        Ex: For product attribute we need to add the attribute_id in the payload

        :returns: list of API response keys that are not updatable
        """
        return []

    @property
    def uid(self) -> Optional[Union[str, int]]:
        """Unique item identifier; used in the url of the :meth:`~.Model.data_endpoint`.

        It's default None for when the model is set to be created
        """
        return self.data.get(self.IDENTIFIER, None)

    def data_endpoint(self, scope: Optional[str] = None) -> str:
        """Endpoint to use when requesting/updating the item's data

        :param scope: the scope to generate the :meth:`~.url_for`
        """
        return self.client.url_for(f'{self.endpoint}/{self.uid}', scope)

    def query_endpoint(self) -> Manager:
        """Initializes and returns the :class:`~.Manager` object corresponding to the Model's ``endpoint``

        :returns: a :class:`~.Manager` or subclass, depending on the ``endpoint``
        """
        return self.client.manager(self.list_endpoint)

    def parse(self, response: dict) -> Model:
        """Uses the instance's corresponding :class:`~.Manager` to parse an API response

        :param response: API response dict to use as source data
        :returns: a :class:`~.Model` with the same ``endpoint`` as the calling instance
        """
        return self.query_endpoint().parse(response)

    def refresh(self, scope: Optional[str] = None) -> bool:
        """Updates object attributes in place using current data from the :meth:`~.data_endpoint`

        .. hint:: :meth:`~.refresh` can be used to switch the scope of the source data
           without creating a new object or changing the :attr:`.Client.scope`

           .. admonition:: Example
              :class: example

              ::

                # Get product data on 'default' scope
                >>> product = client.products.by_sku('sku42')
                # Get fresh product data from different scope
                >>> product.refresh('all')

                Refreshed <Magento Product: sku42> on scope all

        :param scope: the scope to send the request on; uses the :attr:`.Client.scope` if not provided
        """
        url = self.data_endpoint(scope)
        response = self.client.get(url)

        if response.ok:
            self.clear(*self.cached)
            self.set_attrs(response.json())
            self._fetched = True
            self.logger.info(
                f"Refreshed {self} on scope {self.get_scope_name(scope)}"
            )
            return True
        else:
            error_message = (f"Failed to fetch {self} on scope {self.get_scope_name(scope)} with UUID {self.uid}")

            self.logger.error(error_message)
            if self.client.strict_mode:
                raise InstanceGetFailed(error_message)

            return False


    def validate_model_method(self, method: ModelMethod) -> None:
        """
        Validates whether the specified method is allowed for this model.
        Raises an OperationNotAllowedError if the method is not allowed.

        :param method: The ModelMethod to validate (e.g., ModelMethod.CREATE, ModelMethod.UPDATE)
        :raises OperationNotAllowedError: if the method is not allowed for this model.
        """
        if method not in self.ALLOWED_METHODS:
            raise OperationNotAllowedError(self.client, method.name, self.__class__.__name__)

    def clear_mutable_data(self):
        self.mutable_data = {}

    @validate_method_for_model(ModelMethod.UPDATE)
    def save(self, add_save_options: bool = False, scope: Optional[str] = None, refresh: bool = True) -> bool:
        """Save the instance with the provided attribute data.

        This method compares the mutable initial values with the mutable data keys,
        builds the update payload, sends the PUT request to the appropriate endpoint,
        and refreshes the instance with the latest data if the save is successful.

        :param add_save_options: Whether to add the 'save_options' flag to the payload.
        :param scope: The scope to send the request on; will use the default scope if not provided.
        :param refresh: Decode of we perform refresh after create
        :returns: Boolean indicating the success of the save operation.
        """

        if not self._fetched:
            # this will make sure mutable_data have all the values
            create_data = {}
            for key in self.mutable_initial_values.keys():
                create_data[key] = getattr(self, key)

            # we don't need to do any checks because we couldn't get this far (past __init__) if we were missing required keys
            for key in self.required_keys:
                if key not in create_data:
                    create_data[key] = getattr(self, key)

            for key, value in self.mutable_data.items():
                if key not in create_data:
                    create_data[key] = value

            instance = self.client.manager(self.endpoint).create(data=create_data, scope=scope)

            if instance:
                self.set_attrs(instance.data)
            else:
                if refresh:
                    self.refresh(scope)
                    self.clear_mutable_data()

            return True

        # Build the data by comparing mutable_initial_values with mutable_data
        data = {
            key: value
            for key, value in self.mutable_data.items()
            if self.mutable_initial_values.get(key) != value
        }

        # If no data changes are detected
        if not data:
            self.logger.info(f'Nothing to change for instance {self.__class__.__name__} with ID: {self.uid}')
            return True


        # Ensure all required keys are present in the data
        for key in self.required_keys:
            data[key] = self.data.get(key)

        # we add to the payload required attributes that can't be updated but are required for the update to work
        for key in self.required_for_update_keys:
            if key not in data and hasattr(self, key):
                data[key] = getattr(self, key)

        payload_prefix = get_payload_prefix(endpoint=self.endpoint, payload_prefix=self.PAYLOAD_PREFIX)

        # Add the prefix to the data
        payload = {payload_prefix: data}

        # Add save options if needed
        if add_save_options:
            payload['save_options'] = True

        payload = self.enchance_payload(payload)

        # Send the PUT request
        url = self.data_endpoint(scope)
        response = self.client.put(url, payload)

        if response.ok:
            if refresh:
                self.refresh(scope)
                self.clear_mutable_data()
            self.logger.info(f'{self.__class__.__name__} with data: {data} was successfully updated.')
            return True
        else:
            error_message = (
                f'Failed to update {self.__class__.__name__} with status code {response.status_code}.\n'
                f'Message: {MagentoError.parse(response)}'
            )

            self.logger.error(error_message)
            if self.client.strict_mode:
                raise InstanceUpdateFailed(error_message)
            return False

    @validate_method_for_model(ModelMethod.DELETE)
    def delete(self) -> bool:
        """Deletes the instance.

        .. hint:: If you delete an instance by accident, the object's ``data``
         attribute will still contain the raw data, which can be used to recover it.

         Alternatively, don't delete it by accident.
        """
        url = self.data_endpoint()
        response = self.client.delete(url)

        if response.ok and response.json() is True:
            self.logger.info(f'Deleted {self.__class__.__name__} with UID {self.uid}')
            return True
        else:
            msg = f'Failed to delete {self.__class__.__name__} with UID {self.uid}. Message: {MagentoError.parse(response)}'
            self.logger.error(msg)
            if self.client.strict_mode:
                raise InstanceDeleteFailed(msg)
            return False

    @staticmethod
    def unpack_attributes(attributes: List[dict], key: str = 'attribute_code') -> dict:
        """Unpacks a list of attribute dictionaries into a single dictionary

        .. admonition:: Example
           :class: example

           ::

            >> custom_attrs = [{'attribute_code': 'attr', 'value': 'val'},{'attribute_code': 'will_to_live', 'value': '0'}]
            >> print(Model.unpack_attributes(custom_attrs))

            {'attr': 'val', 'will_to_live': '0'}

        :param attributes: a list of custom attribute dictionaries
        :param key: the key used in the attribute dictionary (ex. ``attribute_code`` or ``label``)
        :returns: a single dictionary of all custom attributes formatted as ``{"attr": "val"}``
        """
        return {attr[key]: attr['value'] for attr in attributes}

    @staticmethod
    def pack_attributes(attribute_data: dict, key: str = 'attribute_code') -> List[dict]:
        """Packs a dictionary containing attributes into a list of attribute dictionaries

        .. admonition:: **Example**
           :class: example

           ::

            >> attribute_data = {'special_price': 12, 'meta_title': 'My Product'}
            >> print(Model.pack_attributes(attribute_data))
            >> print(Model.pack_attributes(attribute_data, key='label'))

            [{'attribute_code': 'special_price', 'value': 12}, {'attribute_code': 'meta_title', 'value': 'My Product'}]
            [{'label': 'special_price', 'value': 12}, {'label': 'meta_title', 'value': 'My Product'}]


        :param attribute_data: a dictionary containing attribute data
        :param key: the key to use when packing the attributes (ex. ``attribute_code`` or ``label``)
        :returns: a list of dictionaries formatted as ``{key : "attr", "value": "value"}``
        """
        return [{key: attr, "value": val} for attr, val in attribute_data.items()]

    @staticmethod
    def encode(string: str) -> str:
        """URL-encode with :mod:`urllib.parse`; used for requests that could contain special characters

        :param string: the string to URL-encode
        """
        if urllib.parse.unquote_plus(string) != string:
            return string  # Already encoded
        return urllib.parse.quote_plus(string)

    @cached_property
    def cached(self) -> List[str]:
        """Names of properties that are wrapped with :func:`functools.cached_property`"""
        return [member for member, val in inspect.getmembers(self.__class__) if
                isinstance(val, cached_property) and member != 'cached']

    def clear(self, *keys: str) -> None:
        """Deletes the provided keys from the object's :attr:`__dict__`

        To clear all cached properties::

            >> self.clear(*self.cached)

        :param keys: name of the object attribute(s) to delete
        """
        for key in keys:
            self.__dict__.pop(key, None)
        self.logger.debug(f'Cleared {keys} from {self}')

    def get_scope_name(self, scope: str) -> str:
        """Returns the appropriate scope name to use for logging messages"""
        return scope or 'default' if scope is not None else self.client.scope or 'default'

    def enchance_payload(self, payload):
        """Method that allow override to the create payload"""
        return payload


class APIResponse(Model):

    IDENTIFIER = 'entity_id'  # Most endpoints use this field

    def __init__(self, data: dict, client: clients.Client, endpoint: str, fetched: bool = False):
        """A generic :class:`Model` subclass

        Wraps API responses when there isn't a :class:`Model` subclass defined for the ``endpoint``

        :param data: the API response from an API endpoint
        :param client: an initialized :class:`~.Client` object
        :param endpoint: the endpoint that the API response came from
        """
        super().__init__(
            data=data,
            client=client,
            endpoint=endpoint,
            fetched=fetched
        )

    @property
    def excluded_keys(self) -> List[str]:
        return []

    @property
    def uid(self) -> Optional[int]:
        """Unique item identifier

        .. note:: Since the :class:`~.APIResponse` can wrap any endpoint, the response
           is checked for commonly used id fields (``entity_id`` and ``id``)

           If the endpoint doesn't use those fields, ``None`` will be returned
        """
        if not (uid := super().uid):
            uid = self.data.get('id', None)
        return uid

    def data_endpoint(self, scope: Optional[str] = None) -> Optional[str]:
        if self.uid:
            return super().data_endpoint(scope)
        else:
            self.logger.info(
                f'Unable to determine uid field for API response from "{self.endpoint}"')

class FetchedOnlyModel(Model):
    """
    A subclass of Model that cannot be directly instantiated for creation.

    We can create this model only by the manager create method. This model is both stand alone but crete depends on other models.
    Ex. Shipment that it's own get / search and many more apis but the create depends on Order and OrderItems.
    """

    def __init__(self, data: dict, client: clients.Client, endpoint: str, fetched: bool = False, list_endpoint: Optional[str] = None):
        """Initialize a NonInitiableModel object, ensuring it cannot be created directly."""
        if not fetched:
            raise OperationNotAllowedError(self.client, 'INIT', self.__class__.__name__)

        super().__init__(data, client, endpoint, fetched=fetched, list_endpoint=list_endpoint)

    @classmethod
    def create(cls, *args, **kwargs):
        """Custom create method to handle specific creation logic."""
        raise NotImplementedError(f"{cls.__name__} must be created using a custom method.")
