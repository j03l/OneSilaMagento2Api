from __future__ import annotations
from typing import Union, List, Optional, TYPE_CHECKING
from .manager import Manager
from ..models import Product, Order, Invoice, Customer

if TYPE_CHECKING:
    from . import Client


class CustomerManager(Manager):
    """:class:`ManagerQuery` subclass for the ``customers/search`` endpoint"""

    def __init__(self, client: Client):
        """Initialize a :class:`CustomerManager`

        :param client: an initialized :class:`~.Client` object
        """
        super().__init__(
            endpoint='customers/search',
            client=client,
            model=Customer
        )

    def by_id(self, item_id: Union[int, str]) -> Optional[Customer]:
        self.query = self.query.replace('customers/search', 'customers')
        return super().by_id(item_id)

    def by_first_name(self, name):
        return self.add_criteria('firstName', name).execute_search(apply_pagination=False)

    def by_last_name(self, name):
        return self.add_criteria('lastName', name).execute_search(apply_pagination=False)

    def by_invoice(self, invoice: Invoice):
        return self.by_order(invoice.order)

    def by_order(self, order: Order):
        if customer_id := order.data.get("customer_id"):
            return self.by_id(customer_id)
        else:
            return self.client.logger.info(
                f"No customer account exists for {order}")

    def by_product(self, product: Product) -> Optional[Customer | List[Customer]]:
        orders = product.get_orders() or []
        customer_ids = set()

        if not isinstance(orders, list):
            return self.by_order(orders)

        for order in orders:
            if customer_id := order.data.get('customer_id'):
                customer_ids.add(customer_id)

        return self.by_list('entity_id', customer_ids)
