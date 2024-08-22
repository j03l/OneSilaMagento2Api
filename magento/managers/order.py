from __future__ import annotations
from functools import cached_property
from typing import Union, Iterable, List, Optional, TYPE_CHECKING

from .manager import Manager
from ..models import Model, Product, Category, Order, OrderItem, Customer

if TYPE_CHECKING:
    from . import Client


class OrderManager(Manager):
    """:class:`ManagerQuery` subclass for the ``orders`` endpoint"""

    def __init__(self, client: Client, ):
        """Initialize an :class:`OrderManager`

        :param client: an initialized :class:`~.Client` object
        """
        super().__init__(
            endpoint='orders',
            client=client,
            model=Order
        )

    def by_number(self, order_number: Union[int, str]) -> Optional[Order]:
        """Retrieve an :class:`~.Order` by number

        :param order_number: the order number (``increment_id``)
        """
        return self.add_criteria(
            field='increment_id',
            value=order_number
        ).execute_search()

    def by_product(self, product: Product) -> Optional[Order | List[Order]]:
        """Manager for all :class:`~.Order` s of a :class:`~.Product`

        :param product: the :class:`~.Product` to search for in orders
        """
        items = self.client.order_items.by_product(product)
        return self.from_items(items)

    def by_sku(self, sku: str) -> Optional[Order | List[Order]]:
        """Manager for :class:`~.Order` by product sku

        .. note:: Like :meth:`.OrderItemManager.by_sku`, the sku will need to be an exact
           match to the sku of a simple product, including a custom option if applicable

           * Use :meth:`~.OrderManager.by_product` or :meth:`~.OrderManager.by_product_id`
             to find orders containing any of the :attr:`~.option_skus` and/or all
             :attr:`~.children` of a configurable product

        :param sku: the exact product sku to search for in orders
        """
        items = self.client.order_items.by_sku(sku)
        return self.from_items(items)

    def by_product_id(self, product_id: Union[int, str]) -> Optional[Order | List[Order]]:
        """Manager for :class:`~.Order` s by ``product_id``

        :param product_id: the ``id`` (``product_id``) of the product to search for in orders
        """
        items = self.client.order_items.by_product_id(product_id)
        return self.from_items(items)

    def by_category_id(self, category_id: Union[int, str], search_subcategories: bool = False) -> Optional[Order | List[Order]]:
        """Manager for :class:`~.Order` s by ``category_id``

        :param category_id: id of the category to search for in orders
        :param search_subcategories: if ``True``, also searches for orders from :attr:`~.all_subcategories`
        :returns: any :class:`~.Order` containing a :class:`~.Product` in the corresponding :class:`~.Category`
        """
        items = self.client.order_items.by_category_id(category_id, search_subcategories)
        return self.from_items(items)

    def by_category(self, category: Category, search_subcategories: bool = False) -> Optional[Order | List[Order]]:
        """Manager for :class:`~.Order` s that contain any of the category's :attr:`~.Category.products`

        :param category: the :class:`~.Category` to use in the search
        :param search_subcategories: if ``True``, also searches for orders from :attr:`~.all_subcategories`
        :returns: any :class:`~.Order` that contains a product in the provided category
        """
        items = self.client.order_items.by_category(category, search_subcategories)
        return self.from_items(items)

    def by_skulist(self, skulist: Union[str, Iterable[str]]) -> Optional[Order | List[Order]]:
        """Manager for :class:`~.Order` s using a list or comma separated string of product SKUs

        :param skulist: an iterable or comma separated string of product SKUs
        """
        items = self.client.order_items.by_skulist(skulist)
        return self.from_items(items)

    def by_customer(self, customer: Customer) -> Optional[Order | List[Order]]:
        """Manager for :class:`~.Order` s by :class:`~.Customer`

        :param customer: the :class:`~.Customer` to retrieve orders from
        """
        return self.by_customer_id(customer.uid)

    def by_customer_id(self, customer_id: Union[int, str]) -> Optional[Order | List[Order]]:
        """Manager for :class:`~.Order` s by ``customer_id``

        :param customer_id: the ``id`` of the customer to retrieve orders for
        """
        return self.add_criteria(
            field='customer_id',
            value=str(customer_id)
        ).execute_search()

    def from_items(self, items: Optional[OrderItem | List[OrderItem]]) -> Optional[Order, List[Order]]:
        """Retrieve unique :class:`~.Order` objects from :class:`~.OrderItem` entries using a single request

        :param items: an individual/list of order items
        """
        if items is None:
            return
        if isinstance(items, list):
            order_ids = set(item.order_id for item in items)
            return self.by_list('entity_id', order_ids)
        else:
            return items.order  # Single OrderItem


class OrderItemManager(Manager):
    """:class:`ManagerQuery` subclass for the ``orders/items`` endpoint"""

    def __init__(self, client: Client):
        """Initialize an :class:`OrderItemManager`

        :param client: an initialized :class:`~.Client` object
        """
        super().__init__(
            endpoint='orders/items',
            client=client,
            model=OrderItem
        )

    @cached_property
    def result(self) -> Optional[OrderItem | List[OrderItem]]:
        if result := super().result:
            if isinstance(result, list):
                return [item for item in result if item]
        return result

    def parse(self, data) -> Optional[OrderItem]:
        """Overrides :meth:`ManagerQuery.parse` to fully hydrate :class:`~.OrderItem` objects

        Extra validation is required for OrderItems, as duplicated and/or incomplete data is returned
        when the child of a configurable product is searched :meth:`by_sku` or :meth:`by_product`

        :param data: API response data
        """
        if data.get('parent_item'):
            return None
        if parent_id := data.get('parent_item_id'):
            return self.client.order_items.by_id(parent_id)
        else:
            return OrderItem(data, self.client)

    def by_product(self, product: Product) -> Optional[OrderItem | List[OrderItem]]:
        """Manager for :class:`~.OrderItem` entries by :class:`~.Product`

        .. note:: This will match OrderItems that contain

           * Any of the child products of a configurable product
           * Any of the :attr:`~.option_skus` of a product with custom options

        :param product: the :class:`~.Product` to search for in order items
        """
        if not isinstance(product, Product):
            raise TypeError(f'`product` must be of type {Product}')

        if items := self.by_product_id(product.id):
            return items

        self.reset()
        return self.by_sku(product.encoded_sku)

    def by_sku(self, sku: str) -> Optional[OrderItem | List[OrderItem]]:
        """Manager for :class:`~.OrderItem` entries by product sku.

        .. admonition:: The SKU must be an exact match to the OrderItem SKU

           OrderItems always use the SKU of a simple product, including any custom options.
           This means that:

           * Managering the SKU of a configurable product returns nothing
           * If a product has custom options, the search will only find OrderItems
             that contain the specific option sku (or base sku) that's provided

           To search for OrderItems containing all :attr:`~.children` of a
           configurable product and/or all possible :attr:`~.option_skus`,
           use :meth:`~.by_product` or :meth:`~.by_product_id`

        :param sku: the exact product sku to search for in order items
        """
        return self.add_criteria('sku', Model.encode(sku)).execute_search()

    def by_product_id(self, product_id: Union[int, str]) -> Optional[OrderItem | List[OrderItem]]:
        """Manager for :class:`~.OrderItem` entries by product id.

        :param product_id: the ``id`` (``product_id``) of the :class:`~.Product` to search for in order items
        """
        return self.add_criteria('product_id', product_id).execute_search()

    def add_order_id_criteria(self, order_id: Union[int, str]) -> OrderItemManager:
        """Manager for :class:`~.OrderItem` entries by product id.

        :param order_id:We add the criteria for the order id so we can combo it with product / product skus
        """
        self.add_criteria('parent_item_id', order_id)
        return self

    def by_category_id(self, category_id: Union[int, str], search_subcategories: bool = False) -> Optional[OrderItem | List[OrderItem]]:
        """Manager for :class:`~.OrderItem` entries by ``category_id``

        :param category_id: id of the :class:`~.Category` to search for in order items
        :param search_subcategories: if ``True``, also searches for order items from :attr:`~.all_subcategories`
        :returns: any :class:`~.OrderItem` containing a :class:`~.Product` in the corresponding :class:`~.Category`
        """
        if category := self.client.categories.by_id(category_id):
            return self.by_category(category, search_subcategories)

    def by_category(self, category: Category, search_subcategories: bool = False) -> Optional[OrderItem | List[OrderItem]]:
        """Manager for :class:`~.OrderItem` entries that contain any of the category's :attr:`~.Category.products`

        :param category: the :class:`~.Category` to use in the search
        :param search_subcategories: if ``True``, also searches for order items from :attr:`~.all_subcategories`
        """
        if not isinstance(category, Category):
            raise TypeError(f'`category` must be of type {Category}')

        product_ids = category.all_product_ids if search_subcategories else category.product_ids
        return self.by_list('product_id', product_ids)

    def by_skulist(self, skulist: Union[str, Iterable[str]]) -> Optional[OrderItem | List[OrderItem]]:
        """Manager for :class:`~.OrderItem`s using a list or comma-separated string of product SKUs

        :param skulist: an iterable or comma separated string of product SKUs
        """
        if not isinstance(skulist, Iterable):
            raise TypeError(f'`skulist` must be an iterable or comma-separated string of SKUs')
        if isinstance(skulist, str):
            skulist = skulist.split(',')

        skus = map(Model.encode, skulist)
        return self.by_list('sku', skus)
