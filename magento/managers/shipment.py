from __future__ import annotations
from typing import Union, Iterable, List, Optional, TYPE_CHECKING

from .manager import Manager
from ..exceptions import MagentoError, InstanceCreateFailed
from ..models import Model, Order, OrderItem
from ..models.shipment import Shipment
from ..utils import get_payload_prefix

if TYPE_CHECKING:
    from . import Client


class ShipmentManager(Manager):
    """:class:`ManagerQuery` subclass for the `shipments` endpoint."""

    def __init__(self, client: Client):
        """Initialize a :class:`ShipmentManager`.

        :param client: an initialized :class:`~.Client` object
        """
        super().__init__(
            endpoint='shipments',
            create_endpoint='shipment',
            client=client,
            model=Shipment
        )

    def by_order_id(self, order_id: Union[int, str]) -> Optional[Shipment | List[Shipment]]:
        """Retrieve shipments by `order_id`.

        :param order_id: the `order_id` associated with the shipment(s)
        """
        return self.add_criteria(
            field='order_id',
            value=order_id
        ).execute_search()

    def by_customer_id(self, customer_id: Union[int, str]) -> Optional[Shipment | List[Shipment]]:
        """Retrieve shipments by `customer_id`.

        :param customer_id: the `customer_id` associated with the shipment(s)
        """
        return self.add_criteria(
            field='customer_id',
            value=customer_id
        ).execute_search()

    def by_store_id(self, store_id: Union[int, str]) -> Optional[Shipment | List[Shipment]]:
        """Retrieve shipments by `store_id`.

        :param store_id: the `store_id` associated with the shipment(s)
        """
        return self.add_criteria(
            field='store_id',
            value=store_id
        ).execute_search()

    def by_billing_address_id(self, billing_address_id: Union[int, str]) -> Optional[Shipment | List[Shipment]]:
        """Retrieve shipments by `billing_address_id`.

        :param billing_address_id: the `billing_address_id` associated with the shipment(s)
        """
        return self.add_criteria(
            field='billing_address_id',
            value=billing_address_id
        ).execute_search()

    def by_shipping_address_id(self, shipping_address_id: Union[int, str]) -> Optional[Shipment | List[Shipment]]:
        """Retrieve shipments by `shipping_address_id`.

        :param shipping_address_id: the `shipping_address_id` associated with the shipment(s)
        """
        return self.add_criteria(
            field='shipping_address_id',
            value=shipping_address_id
        ).execute_search()

    def by_id(self, item_id: Union[int, str]) -> Optional[Model]:
        """Retrieve a Shipment by its ID.

        :param item_id: The ID of the shipment.
        """
        url = self.client.url_for(f'shipment/{item_id}')
        response = self.client.get(url)

        if response.ok:
            return self.parse(response.json())

        return None

    def create_shipment(self, order: Order, items: List[OrderItem], quantities: List[int], data: Optional[dict] = None, scope: Optional[str] = None) -> Optional[Shipment]:
        """Create a new shipment instance with the provided data.

        :param order: The order associated with the shipment.
        :param items: A list of OrderItem objects that are being shipped.
        :param quantities: A list of quantities corresponding to each OrderItem.
        :param data: The dict instance containing additional attributes for the new shipment.
        :param scope: Optional scope for the request.
        :return: The newly created Shipment instance.
        """
        if len(items) != len(quantities):
            raise ValueError("The length of items and quantities must match.")

        if data is None:
            data = {}

        shipment_items = []
        for item, qty in zip(items, quantities):
            shipment_items.append({
                'order_item_id': item.item_id,
                'qty': qty,
                'product_id': item.product_id,
                'sku': item.sku,
                'name': item.name,
                'price': item.price,
                'row_total': item.row_total,
                'weight': item.row_weight,  # assuming this field is optional and can be set to 0 if not applicable
            })

        shipment_data = {
            'order_id': order.uid,  # Assuming 'uid' is the order ID
            'items': shipment_items,
            'total_qty': sum(quantities),
            'tracks': [],  # Empty array as tracks will be added later
            'comments': [],  # Empty array as comments will be added later
        }

        # Merge additional data provided by the user
        shipment_data.update(data)

        payload_prefix = get_payload_prefix(endpoint=self.create_endpoint, payload_prefix=Shipment.PAYLOAD_PREFIX)

        # Construct the final payload with the prefix
        payload = {payload_prefix: shipment_data}

        # Send the POST request to create the shipment instance
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
