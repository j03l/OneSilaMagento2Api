from __future__ import annotations
from typing import Union, Iterable, List, Optional, TYPE_CHECKING

from .manager import Manager, MinimalManager
from ..models import Model, APIResponse, Product, Category, ProductAttribute
from ..models.product import AttributeOption

if TYPE_CHECKING:
    from . import Client

class ProductManager(Manager):
    """:class:`ManagerQuery` subclass for the ``products`` endpoint"""

    def __init__(self, client: Client):
        """Initialize a :class:`ProductManager`

        :param client: an initialized :class:`~.Client` object
        """
        super().__init__(
            endpoint='products',
            client=client,
            model=Product
        )

    @property
    def attributes(self) -> ProductAttributeManager:
        """Alternate way to access the ManagerQuery for :class:`~.ProductAttribute` data"""
        return ProductAttributeManager(self.client)

    def by_id(self, item_id: Union[int, str]) -> Optional[Product]:
        """Retrieve a :class:`~.Product` by ``product_id``

        .. note:: Response data from the ``products`` endpoint only has an ``id`` field, but
           all other endpoints that return data about products will use ``product_id``

        :param item_id: the ``id`` (``product_id``) of the product
        """
        return self.add_criteria(
            field='entity_id',  # Product has no "entity_id" field in API responses
            value=item_id  # But to search by the "id" field, must use "entity_id"
        ).execute_search()

    def by_sku(self, sku) -> Optional[Product]:
        """Retrieve a :class:`~.Product` by ``sku``

        :param sku: the product sku
        """
        return super().by_id(Model.encode(sku))

    def get_default_get_method(self, identifier: str) -> Optional[Model]:
        """Override the main by_id method"""
        return self.by_sku(identifier)

    def by_skulist(self, skulist: Union[str, Iterable[str]]) -> Optional[Product | List[Product]]:
        """Manager for :class:`~.Product`s using a list or comma separated string of SKUs

        :param skulist: an iterable or comma separated string of SKUs
        """
        if not isinstance(skulist, Iterable):
            raise TypeError(f'`skulist` must be an iterable or comma-separated string of SKUs')
        if isinstance(skulist, str):
            skulist = skulist.split(',')

        skus = map(Model.encode, skulist)
        return self.by_list('sku', skus)

    def by_category(self, category: Category, search_subcategories: bool = False) -> Optional[Product | List[Product]]:
        """Manager for :class:`~.Product` s in a :class:`~.Category`

        :param category: the :class:`~.Category` to retrieve products from
        :param search_subcategories: if ``True``, also retrieves products from :attr:`~.all_subcategories`
        """
        if not isinstance(category, Category):
            raise TypeError(f'`category` must be of type {Category}')

        if search_subcategories:
            category_ids = [category.id] + category.all_subcategory_ids
            return self.by_list('category_id', category_ids)
        else:
            return self.add_criteria('category_id', category.id).execute_search()

    def by_category_id(self, category_id: Union[int, str], search_subcategories: bool = False) -> Optional[Product | List[Product]]:
        """Manager for :class:`~.Product` s by ``category_id``

        :param category_id: the id of the :class:`~.Category` to retrieve products from
        :param search_subcategories: if ``True``, also retrieves products from :attr:`~.all_subcategories`
        """
        if search_subcategories:
            if category := self.client.categories.by_id(category_id):
                return self.by_category(category, search_subcategories)
            return None
        else:
            return self.add_criteria('category_id', category_id).execute_search()

    def by_customer_id(self, customer_id: Union[int, str], exclude_cancelled: bool = True):
        """Manager for ordered :class:`~.Product`\s by ``customer_id``

        :param customer_id: the ``id`` of the customer to retrieve ordered products for
        :param exclude_cancelled: flag indicating if products from cancelled orders should be excluded
        :returns: products that the customer has ordered, as an individual or list of :class:`~.Product` objects
        """
        if customer := self.client.customers.by_id(customer_id):
            return customer.get_ordered_products(exclude_cancelled)

    def get_stock(self, sku) -> Optional[int]:
        """Retrieve the :attr:`~.stock` of a product by sku

        :param sku: the product sku
        """
        if product := self.by_sku(sku):
            return product.stock


class ProductAttributeManager(Manager):
    """:class:`ManagerQuery` subclass for the ``products/attributes`` endpoint"""

    def __init__(self, client: Client):
        """Initialize a :class:`ProductAttributeManager`

        :param client: an initialized :class:`~.Client` object
        """
        super().__init__(
            endpoint='products/attributes',
            client=client,
            model=ProductAttribute
        )

    def all(self) -> Optional[List[ProductAttribute]]:
        """Retrieve a list of all :class:`~.ProductAttribute`s"""
        return self.add_criteria('position', 0, 'gteq').execute_search()

    def all_in_memory(self) -> Optional[List[ProductAttribute]]:
        """Retrieve a list of all :class:`~.ProductAttribute`s"""
        return super().all_in_memory()

    def by_code(self, attribute_code: str) -> Optional[ProductAttribute]:
        """Retrieve a :class:`~.ProductAttribute` by its attribute code

        :param attribute_code: the code of the :class:`~.ProductAttribute`
        """
        return self.by_id(attribute_code)

    def get_types(self) -> Optional[List[APIResponse]]:
        """Retrieve a list of all available :class:`~.ProductAttribute` types"""
        return self.client.manager(f'{self.endpoint}/types').execute_search()

    def create(self, data: dict, payload_prefix: Optional[str] = None, scope: Optional[str] = None) -> Optional[Model]:
        if payload_prefix != 'attribute':
            payload_prefix = 'attribute'
        return super().create(data=data, payload_prefix=payload_prefix, scope=scope)


class ProductAttributeOptionManager(MinimalManager):
    """:class:`MinimalManager` subclass for managing attribute options in the ``products/attributes/{attribute_code}/options`` endpoint."""

    def __init__(self, client: Client, attribute: ProductAttribute):
        """Initialize a :class:`ProductAttributeOptionManager`

        :param attribute: The :class:`ProductAttribute` instance to which the options belong.
        """
        # Initialize the MinimalManager with the appropriate endpoint and model
        super().__init__(
            endpoint=f"V1/products/attributes/{attribute.attribute_code}/options",
            client=client,
            model=AttributeOption
        )
        self.attribute = attribute

    def __repr__(self):
        return f"<ProductAttributeOptionManager for {self.attribute.attribute_code}>"

    def by_label(self, label: str) -> Optional[AttributeOption]:
        """Retrieve an AttributeOption by its label.

        :param label: The label of the option.
        """
        for option in self.attribute.options:
            if option.label == label:
                return option
        self.client.logger.info(f"No option found with label: {label} for {self.attribute}")
        return None

    def all(self) -> List[AttributeOption]:
        """Retrieve all options for the ProductAttribute."""
        return self.attribute.options

    def get_default_get_method(self, identifier: str) -> Optional[AttributeOption]:
        """Override the default get method to retrieve an option by label."""
        return self.by_label(identifier)