from __future__ import annotations

from functools import cached_property

from . import ImmutableModel, Product, ProductAttribute
from typing import TYPE_CHECKING, Optional, List

from ..constants import ModelMethod

if TYPE_CHECKING:
    from magento import Client

class ConfigurableProduct(ImmutableModel):
    """Wrapper for the `configurable-products` endpoint."""

    DOCUMENTATION = 'https://adobe-commerce.redoc.ly/2.3.7-admin/tag/configurable-products/'
    IDENTIFIER = 'sku'
    ALLOWED_METHODS = [ModelMethod.GET, ModelMethod.CREATE, ModelMethod.UPDATE, ModelMethod.DELETE]

    def __init__(self, product: Product, client: Client, fetched: bool = False):
        """
        Initialize a ConfigurableProduct object using an API response from the `configurable-products` endpoint.

        This model have a set of tools to create configurable products but at the end of the day is still a product.
        So don't use this in order to update product fields or things like this. We have the Product model for it.
        """
        self.product = product
        super().__init__(
            data={},
            client=client,
            endpoint='configurable-products',
            fetched=fetched
        )

    def __repr__(self):
        return f"<Magento ConfigurableProduct: {self.product.sku}>"

    # ------------------------------------------------- PROPERTIES

    @property
    def children(self) -> List[Product]:
        """Retrieve the child simple products of a configurable product."""
        response = self.client.get(self.client.url_for(f'{self.endpoint}/{self.product.encoded_sku}/children'))
        return [Product(data=child, client=self.client, fetched=True) for child in response.json()]

    @cached_property
    def options(self) -> List[dict]:
        """Retrieve all options of the configurable product."""
        response = self.client.get(self.client.url_for(f'{self.endpoint}/{self.product.encoded_sku}/options/all'))
        return response.json()

    # ------------------------------------------------- CUSTOM METHODS

    def add_child(self, child_product: Product, attributes: List[ProductAttribute]) -> bool:
        """Add a child product to the configurable product.

        :param child_product: The child product instance to add.
        :param attributes: A list of ProductAttribute instances used to configure the child product.
        :returns: True if the child product was added successfully, False otherwise.
        """
        for index, attribute in enumerate(attributes):
            self.assign_option(attribute, child_product, index)

        # Assign the child product to the configurable product
        return self.assign_child(child_product)

    def assign_child(self, child_product: Product) -> bool:
        """Assign a child product to the configurable product."""
        payload = {
            "childSku": child_product.sku
        }
        response = self.client.post(self.client.url_for(f'{self.endpoint}/{self.product.encoded_sku}/child'), payload)
        return response.ok

    def assign_option(self, attribute: ProductAttribute, child_product: Product, position) -> bool:
        """Assign a specific option to the configurable product for the given attribute."""
        payload = {
            "option": {
                "attribute_id": attribute.attribute_id,
                "label": attribute.default_frontend_label,
                "position": position,
                "is_use_default": True,
                "values": [{"value_index": child_product.id}]
            }
        }
        response = self.client.post(self.client.url_for(f'{self.endpoint}/{self.product.encoded_sku}/options'), payload)
        return response.ok

    def remove_child(self, child_product: Product) -> bool:
        """Remove a child product from the configurable product."""
        response = self.client.delete(self.client.url_for(f'{self.endpoint}/{self.product.encoded_sku}/children/{child_product.sku}'))
        return response.ok

    def remove_option(self, attribute: ProductAttribute) -> bool:
        """Remove a specific option from the configurable product."""
        option = next((opt for opt in self.options if opt['attribute_id'] == attribute.attribute_id), None)
        if option:
            option_id = option['id']
            response = self.client.delete(self.client.url_for(f'{self.endpoint}/{self.product.encoded_sku}/options/{option_id}'))
            return response.ok

        return False

