from __future__ import annotations
from typing import Union, Iterable, List, Optional, TYPE_CHECKING

from .manager import Manager
from ..models import Product, Category, Order, OrderItem, Invoice, Customer

if TYPE_CHECKING:
    from . import Client

class InvoiceManager(Manager):
    """:class:`ManagerQuery` subclass for the ``invoices`` endpoint"""

    def __init__(self, client: Client):
        """Initialize an :class:`InvoiceManager`

        :param client: an initialized :class:`~.Client` object
        """
        super().__init__(
            endpoint='invoices',
            client=client,
            model=Invoice
        )

    def by_number(self, invoice_number: Union[int, str]) -> Optional[Invoice]:
        """Retrieve an :class:`~.Invoice` by number

        :param invoice_number: the invoice number (``increment_id``)
        """
        return self.add_criteria(
            field='increment_id',
            value=invoice_number
        ).execute_search()

    def by_order_number(self, order_number: Union[int, str]) -> Optional[Invoice]:
        """Retrieve an :class:`~.Invoice` by order number

        :param order_number: the order number (``increment_id``)
        """
        if order := self.client.orders.by_number(order_number):
            return self.by_order(order)

    def by_order(self, order: Order) -> Optional[Invoice]:
        """Retrieve the :class:`~.Invoice` for an :class:`~.Order`

        :param order: the :class:`~.Order` object to retrieve an invoice for
        """
        return self.by_order_id(order.id)

    def by_order_id(self, order_id: Union[int, str]) -> Optional[Invoice]:
        """Retrieve an :class:`~.Invoice` by ``order_id``

        :param order_id: the ``order_id`` of the order to retrieve an invoice for
        """
        return self.add_criteria(
            field='order_id',
            value=order_id
        ).execute_search()

    def by_product(self, product: Product) -> Optional[Invoice | List[Invoice]]:
        """Manager for all :class:`~.Invoice` s of a :class:`~.Product`

        :param product: the :class:`~.Product` to search for in invoices
        """
        items = self.client.order_items.by_product(product)
        return self.from_order_items(items)

    def by_sku(self, sku: str) -> Optional[Invoice | List[Invoice]]:
        """Manager for :class:`~.Invoice` s by product sku

        .. note:: Like :meth:`.OrderItemManager.by_sku`, the sku will need to be an exact
           match to the sku of a simple product, including a custom option if applicable

           * Use :meth:`~.InvoiceManager.by_product` or :meth:`~.InvoiceManager.by_product_id`
             to find orders containing any of the :attr:`~.option_skus` and/or all
             :attr:`~.children` of a configurable product

        :param sku: the exact product sku to search for in invoices
        """
        items = self.client.order_items.by_sku(sku)
        return self.from_order_items(items)

    def by_product_id(self, product_id: Union[int, str]) -> Optional[Invoice | List[Invoice]]:
        """Manager for :class:`~.Invoice` s by ``product_id``

        :param product_id: the ``id`` (``product_id``) of the product to search for in invoices
        """
        items = self.client.order_items.by_product_id(product_id)
        return self.from_order_items(items)

    def by_category_id(self, category_id: Union[int, str], search_subcategories: bool = False) -> Optional[Invoice | List[Invoice]]:
        """Manager for :class:`~.Invoice` s by ``category_id``

        :param category_id: id of the category to search for in orders
        :param search_subcategories: if ``True``, also searches for orders from :attr:`~.all_subcategories`
        :returns: any :class:`~.Invoice` containing a :class:`~.Product` in the corresponding :class:`~.Category`
        """
        items = self.client.order_items.by_category_id(category_id, search_subcategories)
        return self.from_order_items(items)

    def by_category(self, category: Category, search_subcategories: bool = False) -> Optional[Invoice | List[Invoice]]:
        """Manager for :class:`~.Invoice` s that contain any of the category's :attr:`~.Category.products`

        :param category: the :class:`~.Category` to use in the search
        :param search_subcategories: if ``True``, also searches for orders from :attr:`~.all_subcategories`
        :returns: any :class:`~.Invoice` that contains a product in the provided category
        """
        items = self.client.order_items.by_category(category, search_subcategories)
        return self.from_order_items(items)

    def by_skulist(self, skulist: Union[str, Iterable[str]]) -> Optional[Invoice | List[Invoice]]:
        """Manager for :class:`~.Invoice` s using a list or comma separated string of product SKUs

        :param skulist: an iterable or comma separated string of product SKUs
        """
        items = self.client.order_items.by_skulist(skulist)
        return self.from_order_items(items)

    def by_customer(self, customer: Customer) -> Optional[Invoice | List[Invoice]]:
        """Manager for all :class:`~.Invoice` s of a :class:`~.Customer`

        :param customer: the :class:`~.Customer` to search for in invoices
        :returns: any :class:`~.Invoice` associated with the provided :class:`~.Customer`
        """
        return self.by_customer_id(customer.uid)

    def by_customer_id(self, customer_id: Union[int, str]) -> Optional[Invoice | List[Invoice]]:
        """Manager for :class:`~.Invoice` s by ``customer_id``

        :param customer_id: the ``id`` of the customer to retrieve invoices for
        """
        orders = self.client.orders.by_customer_id(customer_id)

        if isinstance(orders, list):
            order_ids = set(order.id for order in orders)
            return self.by_list('order_id', order_ids)
        else:
            return self.by_order_id(orders.id)

    def from_order_items(self, items: Optional[OrderItem | List[OrderItem]]) -> Optional[Invoice, List[Invoice]]:
        """Retrieve unique :class:`~.Invoice` objects from :class:`~.OrderItem` entries using a single request

        .. tip:: Since there is no ``invoices/items`` endpoint, to search for invoices we must first do an
           :class:`OrderItemManager`, then retrieve the ``order_ids`` and search :meth:`~.by_order_id`

        :param items: an individual/list of order items
        """
        if items is None:
            return self.client.logger.info(
                'No matching invoices for this search query'
            )
        if isinstance(items, list):
            order_ids = set(item.order_id for item in items)
            return self.by_list('order_id', order_ids)
        else:
            return self.by_order_id(items.order_id)  # Single OrderItem
