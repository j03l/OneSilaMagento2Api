from __future__ import annotations
import re
from functools import cached_property
from typing import Union, Type, Iterable, List, Optional, Dict, TYPE_CHECKING

import requests

from ..models import Model, APIResponse
from ..exceptions import MagentoError, InstanceCreateFailed, InstanceGetFailed
from .. import clients
from ..utils import get_payload_prefix

if TYPE_CHECKING:
    from typing_extensions import Self
    from . import Client


class Manager:
    """Queries any endpoint that invokes the searchCriteria interface. Parent of all endpoint-specific search classes

    .. tip:: See https://developer.adobe.com/commerce/webapi/rest/use-rest/performing-searches/ for official docs
    """

    def __init__(self, endpoint: str, client: Client, model: Type[Model] = APIResponse, create_endpoint: Optional[str] = None):
        """Initialize a Manager object

        :param endpoint: the base search API endpoint (for example, ``orders``)
        :param client: an initialized :class:`~.Client` object
        :param model: the :class:`~.Model` to parse the response data with; uses :class:`~.APIResponse` if not specified
        """
        if not isinstance(client, clients.Client):
            raise TypeError(f'`client` must be of type {clients.Client}')

        #: The :class:`~.Client` to send the search request with
        self.client = client
        #: The endpoint being queried
        self.endpoint = endpoint
        #: :doc:`models` class to wrap the response with
        self.Model = model
        #: The current url for the search request
        self.query = self.client.url_for(endpoint) + '/?'
        #: Restricted fields, from :meth:`~.restrict_fields`
        self.fields = ''
        #: The raw response data, if any
        self._result = {}
        # current page
        self.page = 1
        # max per page
        self.per_page = 100
        # total pages number
        self.total_pages = None
        # some managers have another endpoints for create but most of it will not
        self.create_endpoint = endpoint
        if create_endpoint:
            self.create_endpoint = create_endpoint

    def add_criteria(self, field, value, condition='eq', **kwargs) -> Self:
        """Add criteria to the search query

        :param field: the API response field to search by
        :param value: the value of the field to compare
        :param condition: the comparison condition
        :param kwargs: additional search option arguments (``group`` and ``filter``)
        :returns: the calling Manager object

        .. admonition:: Keyword Argument Options: ``Condition``
           :class: tip

           The ``condition`` argument specifies the condition used to evaluate the attribute value

           * ``"eq"`` (default): matches items for which ``field=value``
           * ``"gt"``: matches items for which ``field>value``
           * ``"lt"``: matches items for which ``field<value``
           * ``"gteq"``: matches items for which ``field>=value``
           * ``"lteq"``: matches items for which ``field<=value``
           * ``"in"``: matches items for which ``field in value.split(",")``

             - Tip: for ``in``, use :meth:`~.by_list` if not building a complex query

           .. admonition:: Example
              :class: example

              ::

               # Manager for Orders created in 2023
               >>> orders = api.orders.add_criteria(
               ...     field="created_at",
               ...     value="2023-01-01",
               ...     condition='gteq'
               ... ).execute_search()

        .. admonition:: Keyword Argument Options: Using Filter Groups
           :class: hint

           ``group`` - filter group number

           ``filter`` - filter number (within the specified filter group)


        *Using Filter Groups*

            Filter groups are filter criteria in the form of { field: value }

                Group 0 Filter 0                        ->      Filter 0
                Group 0 Filter 0 + Group 0 Filter 1     ->      Filter 0 OR Filter 1
                Group 0 Filter 0 + Group 1 Filter 0     ->      Filter 0 AND Filter 0
        """

        if value is None:
            return self

        options = {
            'condition': condition,
            'group': self.last_group + 1,
            'filter': 0,
        }
        options.update(kwargs)

        criteria = (
                f'searchCriteria[filter_groups][{options["group"]}][filters][{options["filter"]}][field]={field}' +
                f'&searchCriteria[filter_groups][{options["group"]}][filters][{options["filter"]}][value]={value}' +
                f'&searchCriteria[filter_groups][{options["group"]}][filters][{options["filter"]}][condition_type]={options["condition"]}'
        )
        if not self.query.endswith('?'):
            self.query += '&'
        self.query += criteria
        return self

    def restrict_fields(self, fields: Iterable[str]) -> Self:
        """Constrain the API response data to only contain the specified fields

        :param fields: an iterable or comma separated string of fields to include in the response
        :returns: the calling Manager object
        """
        if not isinstance(fields, str):
            if not isinstance(fields, Iterable):
                raise TypeError('"fields" must be a comma separated string or an iterable')
            fields = ','.join(fields)

        if (id_field := self.Model.IDENTIFIER) not in fields:
            fields += f',{id_field}'

        self.fields = f'&fields=items[{fields}]'
        return self

    def sort(self, field: str, direction: str = 'ASC') -> Self:
        """Add sorting parameters to the query."""
        if direction.upper() not in ['ASC', 'DESC']:
            raise ValueError("Direction must be either 'ASC' or 'DESC'")

        # Remove existing sorting parameters if they exist
        self.query = re.sub(r'&?searchCriteria\[sortOrders]\[\d+]\[field]=\w+', '', self.query)
        self.query = re.sub(r'&?searchCriteria\[sortOrders]\[\d+]\[direction]=\w+', '', self.query)

        # Add new sorting parameters. For now we support only one sorting field
        self.sorting = f'&searchCriteria[sortOrders][0][field]={field}&searchCriteria[sortOrders][0][direction]={direction.upper()}'
        self.query += self.sorting
        return self

    def add_pagination(self):
        """Add or replace pagination parameters in the query."""
        # Remove existing pagination parameters if they exist
        self.query = re.sub(r'&?searchCriteria\[currentPage]=\d+', '', self.query)
        self.query = re.sub(r'&?searchCriteria\[pageSize]=\d+', '', self.query)

        # Add new pagination parameters
        self.query += f'&searchCriteria[currentPage]={self.page}&searchCriteria[pageSize]={self.per_page}'
        return self

    def execute_search(self, apply_pagination: bool = True) -> Optional[Model | List[Model]]:
        """Sends the search request using the current :attr:`~.scope` of the :attr:`client`

        .. tip:: Change the :attr:`.Client.scope` to retrieve :attr:`~.result` data
           from different store :attr:`~.views`

        :returns: the search query :attr:`~.result`
        """
        if apply_pagination:
            self.add_pagination()
        response = self.client.get(self.query + self.fields)
        self.__dict__.pop('result', None)
        self._result = response.json()

        if apply_pagination:
            self.update_pagination_info()
        return self.result

    def update_pagination_info(self):
        """Update the pagination information after a search execution."""
        if 'total_count' in self._result:
            self.total_pages = -(-self._result['total_count'] // self.per_page)  # Calculate total pages

    def next(self) -> Self:
        """Move to the next page."""
        if self.page >= (self.total_pages or 1):
            raise ValueError("Already on the last page.")
        self.page += 1
        return self.execute_search()

    def previous(self) -> Self:
        """Move to the previous page."""
        if self.page <= 1:
            raise ValueError("Already on the first page.")
        self.page -= 1
        return self.execute_search()

    def first(self) -> Optional[Model]:
        """Get the first item in the current query."""
        self.page = 1
        self.per_page = 1
        result = self.execute_search()
        if isinstance(result, list) and result:
            return result[0]
        return result

    def last(self) -> Optional[Model]:
        """Get the last item in the current query."""
        self.page = self.total_pages or 1
        self.per_page = 1
        result = self.execute_search()
        if isinstance(result, list) and result:
            return result[-1]
        return result

    def clear_pagination(self) -> None:
        """Reset the pagination settings to their defaults."""
        self.page = 1
        self.per_page = 100

    def all_in_memory(self) -> Optional[List[Model]]:
        """Fetch all pages and store them in memory.

        .. warning:: This method can be performance-intensive for large datasets.
        """
        all_results = []
        self.page = 1
        while True:
            self.client.logger.info("Fetching all data for endpoint {}.Current page {}".format(self.endpoint, self.page))
            result = self.execute_search()
            if not result:
                break
            if isinstance(result, list):
                all_results.extend(result)
            else:
                all_results.append(result)
            if self.page >= self.total_pages:
                break
            self.page += 1
        return all_results

    def by_id(self, item_id: Union[int, str]) -> Optional[Model]:
        """Retrieve data for an individual item by its id

        .. note:: The ``id`` field used is different depending on the endpoint being queried

           * Most endpoints use an ``entity_id`` or ``id``
           * The ``orders/items`` endpoint uses ``item_id``
           * The ``products`` endpoint uses ``product_id``,
             but can also be queried :meth:`~ProductManager.by_sku`

           The :attr:`~.Model.IDENTIFIER` attribute of each :class:`~.Model` contains the appropriate field

        :param item_id: id of the item to retrieve
        """
        self.query = self.query.strip('?') + str(item_id)
        instance =  self.execute_search(apply_pagination=False)

        if self.client.strict_mode and instance is None:
            error_message = f"{self.Model} with uid {item_id} does not exists!"
            self.client.logger.error(error_message)

            raise InstanceGetFailed(error_message)

        return instance

    def by_list(self, field: str, values: Iterable) -> Optional[Model, List[Model]]:
        """Manager for multiple items using an iterable or comma-separated string of field values

        .. admonition:: Examples
           :class: example

           Retrieve :class:`~.Product` with ids from 1 to 10::

            # Values can be a list/tuple/iterable
            >> api.products.by_list('entity_id', range(1,11))

           Manager for :class:`~.Order` that are processing, pending, or completed::

            #  Values can be a comma-separated string
            >> api.orders.by_list('status', 'processing,pending,completed')


        :param field: the API response field to search for matches in
        :param values: an iterable or comma separated string of values
        """
        if not isinstance(values, Iterable):
            raise TypeError('`values` must be an iterable')
        if not isinstance(values, str):
            values = ','.join(f'{value}' for value in values)
        return self.add_criteria(
            field=field,
            value=values,
            condition='in'
        ).execute_search()

    def all(self) -> Optional[Model, List[Model]]:
        """Retrieve all items for the given search endpoint.

        .. warning:: Not guaranteed to work with all endpoints.
        """
        return self.execute_search()

    def since(self, sinceDate: str = None) -> Self:
        """Retrieve items for which ``created_at >= sinceDate``

        **Example**::

            # Retrieve products created in 2023
            >> api.products.since('2023-01-01').execute_search()


        .. tip:: Calling with no arguments retrieves all items

           ::

            # Retrieve all products
            >> api.products.since().execute_search()

        :param sinceDate: the date for response data to start from
        :return: the calling :class:`~Manager`
        """
        return self.add_criteria(
            field='created_at',
            value=sinceDate,
            condition='gteq',
            group=self.last_group + 1,
        )

    def until(self, toDate: str) -> Self:
        """Retrieve items for which ``created_at <= toDate``

        :param toDate: the date for response data to end at (inclusive)
        :return: the calling :class:`~Manager`
        """
        return self.add_criteria(
            field='created_at',
            value=toDate,
            condition='lteq',
            group=self.last_group + 1,
        )

    @cached_property
    def result(self) -> Optional[Model | List[Model]]:
        """The result of the search query, wrapped by the :class:`~.Model` corresponding to the endpoint

        :returns: the API response as either an individual or list of :class:`~.Model` objects
        """
        result = self.validate_result()
        if result is None:
            return result
        if isinstance(result, list):
            return [self.parse(item) for item in result]
        if isinstance(result, dict):
            return self.parse(result)

    def validate_result(self) -> Optional[Dict | List[Dict]]:
        """Parses the response and returns the actual result data, regardless of search approach"""
        if not self._result:
            return None

        if isinstance(self._result, list):
            return self._result

        if self._result.get('message'):  # Error; logged by Client
            return None

        if len(self._result.keys()) > 3:  # Single item, retrieved by id
            return self._result

        if 'items' in self._result:  # All successful responses with search criteria have `items` key
            items = self._result['items']
            if items:  # Response can still be {'items': None} though
                if len(items) > 1:
                    return items
                return items[0]
            else:
                self.client.logger.info(
                    "No matching {} for this search query".format(self.endpoint)
                )
                return None
        # I have no idea what could've gone wrong, sorry :/
        msg = "Manager failed with an unknown error.\nAPI Response: {}".format(self._result)
        raise MagentoError(self.client, msg)

    def parse(self, data: dict) -> Model:
        """Parses the API response with the corresponding :class:`~.Model` object

        :param data: API response data of a single item
        """
        if self.Model is not APIResponse:
            return self.Model(data, self.client, fetched=True)
        return self.Model(data, self.client, self.endpoint, fetched=True)

    def reset(self) -> None:
        """Resets the query and result, allowing the object to be reused"""
        self._result = {}
        self.fields = ''
        self.query = self.client.url_for(self.endpoint) + '/?'
        self.__dict__.pop('result', None)
        self.clear_pagination()

    @property
    def result_count(self) -> int:
        """Number of items that matched the search criteria"""
        if not self._result or not self.result:
            return 0
        if isinstance(self.result, Model):
            return 1
        return len(self.result)

    @property
    def result_type(self) -> Type:
        """The type of the result"""
        return type(self.result)

    @property
    def last_group(self) -> int:
        """The most recent filter group on the query

        :returns: the most recent filter group, or ``-1`` if no criteria has been added
        """
        if self.query.endswith('?'):
            return -1
        return int(re.match(
            r'.*searchCriteria\[filter_groups]\[(\d)]',
            self.query
        ).groups()[-1])

    def get_default_get_method(self, identifier: str) -> Optional[Model]:
        """
        Retrieves an existing instance using a unique identifier.

        :param identifier: The unique identifier for the instance (e.g., `sku` for a product).
        :return: The retrieved Model instance if found, otherwise None.
        """
        return self.by_id(identifier)

    def get_instance_for_create(self, data) -> Model:
        """
        Method to get the instance to be created. It allows override so we don't need to override the whole create

        :param data: The dict instance containing attributes for the new instance.
        """
        return self.Model(data=data, client=self.client)

    def parse_create_id_response(self, id: int) -> Optional[Model]:
        """
        Method to parse the create response for when the response is an  id.

        This care be override in managers like attribute options or
        """
        return self.by_id(id)

    def parse_create_response(self, response: requests.Response) -> Optional[Model]:
        """
        Handles the response from a create operation.

        :param response: The response object from the create request.
        :return: The parsed Model instance if successful, otherwise None.
        """
        if response.ok:
            try:
                json_data = response.json()

                if isinstance(json_data, dict):
                    # If the response is a dict, parse it as usual
                    return self.parse(json_data)

                elif isinstance(json_data, int) or (isinstance(json_data, str) and json_data.isdigit()):
                    # If the response is just an ID, use by_id to retrieve the full instance
                    return self.parse_create_id_response(int(json_data))

            except ValueError as e:
                self.client.logger.error(f"Failed to parse JSON response: {response.content}. Initial error: {str(e)}")
                return None

    def create(self, data: dict, scope: Optional[str] = None, extra_data: Optional[dict] = None) -> Optional[Model]:
        """
        Create a new instance with the provided model instance.

        :param data: The dict instance containing attributes for the new instance.
        :param scope: Optional scope for the request.
        :return: The newly created Model instance.
        """
        instance = self.get_instance_for_create(data=data)

        # Ensure the mutable data is populated with initial values
        for k, v in instance.mutable_initial_values.items():
            if not hasattr(instance, k):
                setattr(instance, k, v)

        # Now, instance.mutable_data contains the full payload for creation
        mutable_data = instance.mutable_data

        # Add required keys if necessary (implement required_keys method in your model if needed)
        required_keys = getattr(instance, 'required_keys', [])
        for key in required_keys:
            if val := instance.data.get(key, None):
                if val is None:
                    raise ValueError(f"Missing required key: {key}")

                mutable_data[key] = val

        payload_prefix = get_payload_prefix(endpoint=self.create_endpoint, payload_prefix=instance.PAYLOAD_PREFIX)

        if extra_data:
            # Handle custom_attributes merging if both mutable_data and extra_data contain it
            if 'custom_attributes' in extra_data and 'custom_attributes' in mutable_data:
                # Merge custom attributes, leaving existing ones intact
                mutable_data['custom_attributes'].update(extra_data['custom_attributes'])
                # Remove custom_attributes from extra_data to prevent overwriting
                extra_data.pop('custom_attributes')

            # Now update mutable_data with any remaining keys in extra_data
            mutable_data.update(extra_data)

        # Construct the final payload with the prefix
        payload = {payload_prefix: mutable_data}

        # for the models that use skeleton we need to set it on the root
        if 'skeleton_id' in mutable_data:
            payload['skeletonId'] = mutable_data.pop('skeleton_id')

        # Send the POST request to create the instance
        url = self.client.url_for(self.create_endpoint, scope=scope)
        response = self.client.post(url, payload)

        if response.ok:
            return self.parse_create_response(response)
        else:
            error_message = (
                f'Failed to create {self.Model.__name__} with status code {response.status_code}.\n'
                f'Message: {MagentoError.parse(response)}'
            )
            self.client.logger.error(error_message)
            if self.client.strict_mode:
                raise InstanceCreateFailed(error_message)

            return None

    def get_or_create(
        self,
        identifier: str,
        data: dict,
        scope: Optional[str] = None,
    ) -> Model:
        """
        Retrieve an existing instance based on the identifier, or create a new one if not found.

        :param identifier: The unique identifier for the instance (e.g., `sku` for a product).
        :param data: Attributes to set on the instance if it needs to be created.
        :param scope: Optional scope for the request.
        :return: The retrieved or newly created Model instance.
        """
        # Try to retrieve the existing instance using the identifier
        instance = self.get_default_get_method(identifier)

        if instance:
            self.client.logger.info(f'{self.Model.__name__} with identifier: {identifier} found.')
            return instance

        # If not found, create a new instance
        self.client.logger.info(f'{self.Model.__name__} with identifier: {identifier} not found. Creating new instance.')
        return self.create(data=data, scope=scope)


class MinimalManager(Manager):
    """
    A minimal manager class for intermediate models that do not support the full searchCriteria interface.

    This class provides basic methods for interacting with models but logs an informational message and returns `None`
    for unsupported methods.

    Typically used for managing models like attribute options, where advanced querying features are not required.
    """

    def add_criteria(self, *args, **kwargs) -> Self:
        self.client.logger.info(f"add_criteria is not supported for {self.Model}")
        return self

    def restrict_fields(self, *args, **kwargs) -> Self:
        self.client.logger.info(f"restrict_fields is not supported for {self.Model}")
        return self

    def sort(self, *args, **kwargs) -> Self:
        self.client.logger.info(f"sort is not supported for {self.Model}")
        return self

    def add_pagination(self, *args, **kwargs):
        self.client.logger.info(f"add_pagination is not supported for {self.Model}")
        return self

    def execute_search(self, *args, **kwargs) -> Optional[Model | List[Model]]:
        self.client.logger.info(f"execute_search is not supported for {self.Model}")
        return None

    def update_pagination_info(self, *args, **kwargs):
        self.client.logger.info(f"update_pagination_info is not supported for {self.Model}")
        return None

    def next(self, *args, **kwargs) -> Self:
        self.client.logger.info(f"next is not supported for {self.Model}")
        return self

    def previous(self, *args, **kwargs) -> Self:
        self.client.logger.info(f"previous is not supported for {self.Model}")
        return self

    def first(self, *args, **kwargs) -> Optional[Model]:
        self.client.logger.info(f"first is not supported for {self.Model}")
        return None

    def last(self, *args, **kwargs) -> Optional[Model]:
        self.client.logger.info(f"last is not supported for {self.Model}")
        return None

    def clear_pagination(self, *args, **kwargs) -> None:
        self.client.logger.info(f"clear_pagination is not supported for {self.Model}")
        return None

    def all_in_memory(self, *args, **kwargs) -> Optional[List[Model]]:
        self.client.logger.info(f"all_in_memory is not supported for {self.Model}")
        return None

    def by_list(self, *args, **kwargs) -> Optional[Model, List[Model]]:
        self.client.logger.info(f"by_list is not supported for {self.Model}")
        return None

    def since(self, *args, **kwargs) -> Self:
        self.client.logger.info(f"since is not supported for {self.Model}")
        return self

    def until(self, *args, **kwargs) -> Self:
        self.client.logger.info(f"until is not supported for {self.Model}")
        return self

    @cached_property
    def result(self) -> Optional[Model | List[Model]]:
        self.client.logger.info(f"result is not supported for {self.Model}")
        return None

    def validate_result(self, *args, **kwargs) -> Optional[Dict | List[Dict]]:
        self.client.logger.info(f"validate_result is not supported for {self.Model}")
        return None

    def parse(self, *args, **kwargs) -> Optional[Model]:
        self.client.logger.info(f"parse is not supported for {self.Model}")
        return None

    def reset(self, *args, **kwargs) -> None:
        self.client.logger.info(f"reset is not supported for {self.Model}")
        return None

    @property
    def result_count(self) -> int:
        self.client.logger.info(f"result_count is not supported for {self.Model}")
        return 0

    @property
    def result_type(self) -> Type:
        self.client.logger.info(f"result_type is not supported for {self.Model}")
        return type(None)

    @property
    def last_group(self) -> int:
        self.client.logger.info(f"last_group is not supported for {self.Model}")
        return -1
