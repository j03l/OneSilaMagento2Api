from __future__ import annotations
from typing import Union, Iterable, List, Optional, TYPE_CHECKING

from .manager import Manager
from ..models import Product, Category, Order, OrderItem, Invoice, Customer
from ..models.attribute_set import AttributeSet

if TYPE_CHECKING:
    from . import Client

class AttributeSetManager(Manager):
    """:class:`ManagerQuery` subclass for the ``attribute-sets`` endpoint"""

    def __init__(self, client: Client):
        """Initialize a :class:`AttributeSetManager`

        :param client: an initialized :class:`~.Client` object
        """
        super().__init__(
            endpoint='products/attribute-sets/sets/list',
            create_endpoint='products/attribute-sets',
            client=client,
            model=AttributeSet
        )

    def by_id(self, attribute_set_id: Union[int, str]) -> Optional[AttributeSet]:
        """Retrieve an :class:`~.AttributeSet` by ``attribute_set_id``

        :param attribute_set_id: the ``attribute_set_id`` of the attribute set
        """
        return self.add_criteria(
            field='attribute_set_id',
            value=attribute_set_id
        ).execute_search()

    def get_default_get_method(self, identifier: str) -> Optional[AttributeSet]:
        """Override the main by_id method"""
        return self.by_id(identifier)

    def by_name(self, name: str) -> Optional[AttributeSet]:
        """Retrieve an :class:`~.AttributeSet` by ``attribute_set_name``

        :param name: the name of the attribute set
        """
        return self.add_criteria(
            field='attribute_set_name',
            value=name
        ).execute_search()