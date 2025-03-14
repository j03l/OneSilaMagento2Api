from __future__ import annotations
import requests
from . import Model
from pathlib import Path
from functools import cached_property
from magento.exceptions import MagentoError, InstanceGetFailed
from typing import Union, TYPE_CHECKING, Optional, List, Dict, Any

from ..constants import ModelMethod
from ..decorators import data_not_fetched_value, set_private_attr_after_setter

if TYPE_CHECKING:
    from magento import Client
    from . import Category, Order, OrderItem, Invoice, Customer


class Product(Model):
    """Wrapper for the ``products`` endpoint"""

    STATUS_ENABLED = 1
    STATUS_DISABLED = 2

    VISIBILITY_NOT_VISIBLE = 1
    VISIBILITY_CATALOG = 2
    VISIBILITY_SEARCH = 3
    VISIBILITY_BOTH = 4

    PRODUCT_TYPE_SIMPLE = "simple"
    PRODUCT_TYPE_CONFIGURABLE = "configurable"

    DOCUMENTATION = 'https://adobe-commerce.redoc.ly/2.3.7-admin/tag/products/'
    IDENTIFIER = 'sku'
    ALLOWED_METHODS = [ModelMethod.GET, ModelMethod.CREATE, ModelMethod.UPDATE, ModelMethod.DELETE]

    def __init__(self, data: dict, client: Client, fetched: bool = False):
        """Initialize a Product object using an API response from the ``products`` endpoint

        :param data: the API response from the ``products`` endpoint
        :param client: an initialized :class:`~.Client` object
        """
        # we do this because if we initialize a product in order to create it there will be missing
        super().__init__(
            data=data,
            client=client,
            fetched=fetched,
            endpoint='products',
        )

    def __repr__(self):
        return f"<Magento Product: {self._sku}>"

    # ------------------------------------------------- PROPERTIES

    @property
    def excluded_keys(self):
        return ['media_gallery_entries']

    @property
    def required_keys(self):
        return [self.IDENTIFIER, 'attribute_set_id']

    @property
    def mutable_keys(self) -> List[str]:
        return [
            'name',
            'attribute_set_id',
            'price',
            'special_price',
            'visibility',
            'type_id',
            'status',
            'stock',
            'backorders',
            'manage_stock',
            'views',
            'short_description',
            'category_ids',
            'meta_title',
            'meta_keyword',
            'meta_description',
            'url_key',
        ]

    @property
    def uid(self) -> Union[str, int]:
        return self.encoded_sku

    @property
    def sku(self) -> str:
        return self._sku

    @property
    @data_not_fetched_value(lambda self: {})
    def stock_item(self) -> dict:
        """Stock data from the StockItem Interface"""
        if hasattr(self, 'extension_attributes'):  # Missing if product was retrieved by id
            if stock_data := self.extension_attributes.get('stock_item', {}):
                return stock_data
        # Use the SKU to refresh attributes with full product data
        self.refresh()
        return self.stock_item

    @property
    @data_not_fetched_value(lambda self: None)
    def stock_item_id(self) -> Optional[int]:
        """Item id of the StockItem, used to :meth:`~.update_stock`"""
        if self.stock_item:
            return self.stock_item['item_id']

    @property
    @data_not_fetched_value(lambda self: self._special_price)
    def special_price(self) -> Optional[float]:
        """The current special (sale) price"""
        try:
            return self.custom_attributes.get('special_price')
        except AttributeError:
            return None

    @property
    @data_not_fetched_value(lambda self: None)
    def thumbnail_link(self) -> Optional[str]:
        """Link of the product's :attr:`~.thumbnail` image"""
        if self.thumbnail:
            return self.thumbnail.link

        return None

    @property
    def encoded_sku(self) -> str:
        """URL-encoded SKU, which is used in request endpoints"""
        return self.encode(self.sku)

    @cached_property
    @data_not_fetched_value(lambda self: [])
    def children(self) -> Optional[List[Product]]:
        """If the Product is a configurable product, returns a list of its child products"""
        if self.type_id == 'configurable':
            url = self.client.url_for(f'configurable-products/{self.encoded_sku}/children')
            if (response := self.client.get(url)).ok:
                return [self.parse(child) for child in response.json()]
            else:
                self.logger.error(f'Failed to get child products of {self}')
        else:
            self.logger.info('Only configurable products have child SKUs')
        return []

    @cached_property
    @data_not_fetched_value(lambda self: None)
    def link(self) -> Optional[str]:
        """Link of the product"""
        if url_key := self.custom_attributes.get('url_key'):
            return self.client.store.active.base_url + url_key + '.html'

    @cached_property
    @data_not_fetched_value(lambda self: [])
    def categories(self) -> Optional[Category | List[Category]]:
        """Categories the product is in, returned as a list of :class:`~.Category` objects"""
        category_ids = self.custom_attributes.get('category_ids', [])
        return self.client.categories.by_list('entity_id', category_ids)

    @cached_property
    @data_not_fetched_value(lambda self: [])
    def media_gallery_entries(self) -> List[MediaEntry]:
        """The product's media gallery entries, returned as a list of :class:`MediaEntry` objects"""
        return [MediaEntry(self, entry, fetched=True) for entry in self.__media_gallery_entries]

    @cached_property
    @data_not_fetched_value(lambda self: None)
    def thumbnail(self) -> Optional[MediaEntry]:
        """The :class:`MediaEntry` corresponding to the product's thumbnail"""
        for entry in self.media_gallery_entries:
            if entry.is_thumbnail:
                return entry

    @cached_property
    @data_not_fetched_value(lambda self: [])
    def option_skus(self) -> Optional[List[str]]:
        """The full SKUs for the product's customizable options, if they exist

        .. hint:: When a product with customizable options is ordered, these SKUs are used by the API when
            retrieving and searching for :class:`~.Order` and :class:`~.OrderItem` data
        """
        option_skus = []
        if hasattr(self, 'options'):
            for option in self.options:
                base_sku = option['product_sku']
                for val in option['values']:
                    if val.get('sku'):
                        option_skus.append(base_sku + '-' + val['sku'])
        return option_skus

    @property
    def name(self) -> Optional[str]:
        return self._name

    @property
    def attribute_set_id(self) -> Optional[int]:
        return self._attribute_set_id

    @property
    def price(self) -> Optional[float]:
        return self._price

    @property
    def visibility(self) -> Optional[int]:
        return self._visibility

    @property
    def type_id(self) -> Optional[str]:
        return self._type_id

    @property
    def status(self) -> Optional[int]:
        return self._status

    @property
    @data_not_fetched_value(lambda self: self._backorders)
    def backorders(self) -> Optional[bool]:
        if self.stock_item:
            return self.stock_item.get('backorders') == 1

    @property
    @data_not_fetched_value(lambda self: self._manage_stock)
    def manage_stock(self) -> Optional[bool]:
        """Whether stock management is enabled for the product."""
        if self.stock_item:
            return self.stock_item.get('manage_stock')


    @property
    @data_not_fetched_value(lambda self: self._stock)
    def stock(self) -> int:
        """Current stock quantity"""
        if self.stock_item:
            return self.stock_item['qty']

    @property
    @data_not_fetched_value(lambda self: self._description)
    def description(self) -> Optional[str]:
        """Product description (as HTML)"""
        try:
            return self.custom_attributes.get('description', '')
        except AttributeError:
            return None

    @property
    @data_not_fetched_value(lambda self: self._short_description)
    def short_description(self) -> Optional[str]:
        try:
            return self.custom_attributes.get('short_description')
        except AttributeError:
            return None

    @property
    @data_not_fetched_value(lambda self: self._category_ids)
    def category_ids(self) -> Optional[List[int]]:
        try:
            return self.custom_attributes.get('category_ids')
        except AttributeError:
            return None

    @property
    @data_not_fetched_value(lambda self: self._meta_title)
    def meta_title(self) -> Optional[str]:
        try:
            return self.custom_attributes.get('meta_title')
        except AttributeError:
            return None

    @property
    @data_not_fetched_value(lambda self: self._meta_keyword)
    def meta_keyword(self) -> Optional[str]:
        try:
            return self.custom_attributes.get('meta_keyword')
        except AttributeError:
            return None

    @property
    @data_not_fetched_value(lambda self: self._meta_description)
    def meta_description(self) -> Optional[str]:
        try:
            return self.custom_attributes.get('meta_description')
        except AttributeError:
            return None

    @property
    @data_not_fetched_value(lambda self: self._url_key)
    def url_key(self) -> Optional[str]:
        try:
            return self.custom_attributes.get('url_key')
        except AttributeError:
            return None

    @property
    @data_not_fetched_value(lambda self: [])
    def views(self) -> Optional[list]:
        """
        Retrieves the website_ids from extension_attributes if available.
        """
        return self.extension_attributes.get('website_ids', [])

    # ------------------------------------------------- PROPERTIES SETTERS (the ones that can be updateD)

    @name.setter
    @set_private_attr_after_setter
    def name(self, value: Optional[str]) -> None:
        self.mutable_data['name'] = value

    @sku.setter
    @set_private_attr_after_setter
    def sku(self, value: str) -> None:
        self.mutable_data['sku'] = value
    @attribute_set_id.setter
    @set_private_attr_after_setter
    def attribute_set_id(self, value: Optional[int]) -> None:
        self.mutable_data['attribute_set_id'] = value

    @price.setter
    @set_private_attr_after_setter
    def price(self, value: Optional[float]) -> None:
        self.mutable_data['price'] = value

    @visibility.setter
    @set_private_attr_after_setter
    def visibility(self, value: Optional[int]) -> None:
        self.mutable_data['visibility'] = value

    @type_id.setter
    @set_private_attr_after_setter
    def type_id(self, value: Optional[str]) -> None:
        self.mutable_data['type_id'] = value

    @status.setter
    def status(self, value: Optional[int]) -> None:
        if value is True:
            value = self.STATUS_ENABLED
        elif value is False:
            value = self.STATUS_DISABLED

        self.mutable_data['status'] = value
        self._status = value

    @stock.setter
    @set_private_attr_after_setter
    def stock(self, value: Optional[int]) -> None:
        # Initialize extension_attributes if not present
        self.mutable_data.setdefault('extension_attributes', {})
        stock_item = self.mutable_data['extension_attributes'].setdefault('stock_item', {})

        stock_item["qty"] = value
        stock_item["is_in_stock"] = value is not None and value > 0

        if hasattr(self, 'self'):
            if self.type_id == self.PRODUCT_TYPE_CONFIGURABLE:
                stock_item["is_in_stock"] = True

        if self.stock_item:
            self.stock_item['qty'] = value

        if self.stock_item:
            self.stock_item['is_in_stock'] = stock_item["is_in_stock"]

    @backorders.setter
    @set_private_attr_after_setter
    def backorders(self, value: Optional[bool]) -> None:
        if value is not None:
            self.mutable_data.setdefault('extension_attributes', {})
            stock_item = self.mutable_data['extension_attributes'].setdefault('stock_item', {})

            # Update the relevant part of stock_item
            stock_item.update({
                "backorders": 1 if value else 0,
                "use_config_backorders": False if value else True
            })

            if self.stock_item:
                self.stock_item['backorders'] = 1 if value else 0

    @manage_stock.setter
    @set_private_attr_after_setter
    def manage_stock(self, value: Optional[bool]) -> None:
        if value is not None:
            self.mutable_data.setdefault('extension_attributes', {})
            stock_item = self.mutable_data['extension_attributes'].setdefault('stock_item', {})

            stock_item.update({
                "manage_stock": value
            })

    @description.setter
    @set_private_attr_after_setter
    def description(self, value: Optional[str | None]) -> None:
        self.mutable_data.setdefault('custom_attributes', [])
        for attr in self.mutable_data['custom_attributes']:
            if attr['attribute_code'] == 'description':
                attr['value'] = value
                break
        else:
            self.mutable_data['custom_attributes'].append({'attribute_code': 'description', 'value': value})

        self._update_internal_custom_attribute('description', value)

    @special_price.setter
    @set_private_attr_after_setter
    def special_price(self, value: Optional[str]) -> None:
        self.mutable_data.setdefault('custom_attributes', [])
        for attr in self.mutable_data['custom_attributes']:
            if attr['attribute_code'] == 'special_price':
                attr['value'] = value
                break
        else:
            self.mutable_data['custom_attributes'].append({'attribute_code': 'special_price', 'value': value})

        self._update_internal_custom_attribute('special_price', value)

    @short_description.setter
    @set_private_attr_after_setter
    def short_description(self, value: Optional[str | None]) -> None:
        self.mutable_data.setdefault('custom_attributes', [])
        for attr in self.mutable_data['custom_attributes']:
            if attr['attribute_code'] == 'short_description':
                attr['value'] = value
                break
        else:
            self.mutable_data['custom_attributes'].append({'attribute_code': 'short_description', 'value': value})

        self._update_internal_custom_attribute('short_description', value)

    @category_ids.setter
    @set_private_attr_after_setter
    def category_ids(self, value: Optional[List[int]]) -> None:
        if value:
            self.mutable_data.setdefault('custom_attributes', [])
            for attr in self.mutable_data['custom_attributes']:
                if attr['attribute_code'] == 'category_ids':
                    attr['value'] = value
                    break
            else:
                self.mutable_data['custom_attributes'].append({'attribute_code': 'category_ids', 'value': value})

        self._update_internal_custom_attribute('category_ids', value)

    @meta_title.setter
    @set_private_attr_after_setter
    def meta_title(self, value: Optional[str | None]) -> None:
        self.mutable_data.setdefault('custom_attributes', [])
        for attr in self.mutable_data['custom_attributes']:
            if attr['attribute_code'] == 'meta_title':
                attr['value'] = value
                break
        else:
            self.mutable_data['custom_attributes'].append({'attribute_code': 'meta_title', 'value': value})

        self._update_internal_custom_attribute('meta_title', value)

    @meta_keyword.setter
    @set_private_attr_after_setter
    def meta_keyword(self, value: Optional[str | None]) -> None:
        self.mutable_data.setdefault('custom_attributes', [])
        for attr in self.mutable_data['custom_attributes']:
            if attr['attribute_code'] == 'meta_keyword':
                attr['value'] = value
                break
        else:
            self.mutable_data['custom_attributes'].append({'attribute_code': 'meta_keyword', 'value': value})

        self._update_internal_custom_attribute('meta_keyword', value)

    @meta_description.setter
    @set_private_attr_after_setter
    def meta_description(self, value: Optional[str | None]) -> None:
        self.mutable_data.setdefault('custom_attributes', [])
        for attr in self.mutable_data['custom_attributes']:
            if attr['attribute_code'] == 'meta_description':
                attr['value'] = value
                break
        else:
            self.mutable_data['custom_attributes'].append({'attribute_code': 'meta_description', 'value': value})

        self._update_internal_custom_attribute('meta_description', value)

    @url_key.setter
    @set_private_attr_after_setter
    def url_key(self, value: Optional[str]) -> None:
        if value:
            self.mutable_data.setdefault('custom_attributes', [])
            for attr in self.mutable_data['custom_attributes']:
                if attr['attribute_code'] == 'url_key':
                    attr['value'] = value
                    break
            else:
                self.mutable_data['custom_attributes'].append({'attribute_code': 'url_key', 'value': value})

            self._update_internal_custom_attribute('url_key', value)

    @views.setter
    @set_private_attr_after_setter
    def views(self, value: Optional[list]) -> None:
        """
        Sets the website_ids within extension_attributes to the provided list of IDs.
        """
        if value is not None:
            self.mutable_data.setdefault('extension_attributes', {})
            self.mutable_data['extension_attributes']['website_ids'] = value

            if not hasattr(self, 'extension_attributes'):
                self.extension_attributes = {}

            self.extension_attributes['website_ids'] = value

    # ------------------------------------------------- CUSTOM METHODS

    def update_stock(self, qty: int) -> bool:
        """Updates the stock quantity

        :param qty: the new stock quantity
        """
        url = f'{self.data_endpoint()}/stockItems/{self.stock_item_id}'
        payload = {
            "stock_item": {
                "qty": qty,
                "is_in_stock": qty > 0
            },
            'save_options': True
        }
        response = self.client.put(url, payload)

        if response.ok:
            self.refresh()
            self.logger.info(f'Updated stock to {self.stock} for {self}')
            return True

        else:
            self.logger.error(
                f'Failed to update stock for {self} with status code {response.status_code}' + '\n' +
                f'Message: {MagentoError.parse(response)}'
            )
            return False

    def update_status(self, status: int) -> bool:
        """Update the product status

        :param status: either 1 (for :attr:`~.STATUS_ENABLED`) or 2 (for :attr:`~.STATUS_DISABLED`)
        """
        if status not in [Product.STATUS_ENABLED, Product.STATUS_DISABLED]:
            raise ValueError('Invalid status provided')

        return self.update_attributes({'status': status})

    def update_price(self, price: Union[int, float]) -> bool:
        """Update the product price

        :param price: the new price
        """
        return self.update_attributes({'price': price})

    def update_special_price(self, price: Union[float, int]) -> bool:
        """Update the product special price

        :param price: the new special price
        """
        if price < self.price:
            return self.update_custom_attributes({'special_price': price})

        self.logger.error(f'Sale price for {self} must be less than current price ({self.price})')
        return False

    def update_name(self, name: str, scope: Optional[str] = None) -> bool:
        """Update the product name

        :param name: the new name to use
        :param scope: the scope to send the request on; will use the :attr:`.Client.scope` if not provided
        """
        return self.update_attributes({'name': name}, scope)

    def update_description(self, description: str, scope: Optional[str] = None) -> bool:
        """Update the product description

        :param description: the new HTML description to use
        :param scope: the scope to send the request on; will use the :attr:`.Client.scope` if not provided
        """
        return self.update_custom_attributes({'description': description}, scope)

    def update_metadata(self, metadata: dict, scope: Optional[str] = None) -> bool:
        """Update the product metadata

        :param metadata: the new ``meta_title``, ``meta_keyword`` and/or ``meta_description`` to use
        :param scope: the scope to send the request on; will use the :attr:`.Client.scope` if not provided
        """
        attributes = {k: v for k, v in metadata.items() if k in ('meta_title', 'meta_keyword', 'meta_description')}
        return self.update_custom_attributes(attributes, scope)

    def add_categories(self, category_ids: Union[int, str, List[int | str]]) -> bool:
        """Adds the product to an individual or multiple categories

        :param category_ids: an individual or list of category IDs to add the product to
        """
        if not isinstance(category_ids, list):
            if not isinstance(category_ids, (str, int)):
                raise TypeError(
                    "`category_ids` must be an individual or list of integers/strings"
                )
            category_ids = [category_ids]

        current_ids = self.custom_attributes.get('category_ids', [])
        new_ids = [id for id in map(str, category_ids) if id not in current_ids]
        return self.update_custom_attributes({"category_ids": current_ids + new_ids})

    def remove_categories(self, category_ids: Union[int, str, List[int | str]]) -> bool:
        """Removes the product from an individual or multiple categories

        :param category_ids: an individual or list of category IDs to remove the product from
        """
        if not isinstance(category_ids, list):
            if not isinstance(category_ids, (str, int)):
                raise TypeError(
                    "`category_ids` must be an individual or list of integers/strings"
                )
            category_ids = [category_ids]

        current_ids = self.custom_attributes.get('category_ids', [])
        new_ids = [id for id in current_ids if id not in map(str, category_ids)]
        return self.update_custom_attributes({'category_ids': new_ids})

    def update_attributes(self, attribute_data: dict, scope: Optional[str] = None) -> bool:
        """Update top level product attributes with scoping taken into account

        .. note:: Product attributes can have a ``Global``, ``Store View`` or ``Website`` scope

            :Global Attributes:
                Values are updated on all store views and the admin
            :Website Attributes:
                Values are updated on all store views
            :Store View Attributes:
                Values are updated on the store view specified in the request ``scope``

        A second request will be made to update ``Store View`` and ``Website`` attributes on the admin,
        depending on how many :class:`~.Store` :attr:`~.views` you have:

        * **1 View:** admin values are updated for all attributes, regardless of scope
        * **2+ Views:** admin values are updated only for :attr:`~.website_product_attributes`

        :param attribute_data: a dictionary of product attributes to update
        :param scope: the scope to send the request on; will use the :attr:`.Client.scope` if not provided
        """
        if self.client.store.is_single_store:
            return self._update_single_store(attribute_data)

        if not self._update_attributes(attribute_data, scope):
            return False

        if website_attrs := self.client.store.filter_website_attrs(attribute_data):
            return self._update_attributes(website_attrs, scope='all')
        return True

    def update_custom_attributes(self, attribute_data: dict, scope: Optional[str] = None) -> bool:
        """Update custom attributes with scoping taken into account

        See :meth:`~update_attributes` for details

        .. admonition:: Important
           :class: important-af

           This method only supports updating **custom attributes**

        :param attribute_data: a dictionary of custom attributes to update
        :param scope: the scope to send the request on; will use the :attr:`.Client.scope` if not provided
        """
        attributes = {'custom_attributes': self.pack_attributes(attribute_data)}

        if self.client.store.is_single_store:
            return self._update_single_store(attributes)

        if not self._update_attributes(attributes, scope):
            return False

        if website_attributes := self.client.store.filter_website_attrs(attribute_data):
            return self._update_attributes({'custom_attributes': self.pack_attributes(website_attributes)}, scope='all')
        return True

    def _update_single_store(self, attribute_data: dict) -> bool:
        """Internal function for updating a store with a single store view

        All attributes will be updated on the ``default`` and ``all`` scope,
        ensuring that the frontend and admin always have the same product data

        :param attribute_data: a dictionary of custom product attributes to update
        """
        for store_code in (None, 'all'):
            if not self._update_attributes(attribute_data, store_code):
                return False  # Avoid updating admin if store update fails

        self.refresh()  # Back to default scope
        return True

    def _update_internal_custom_attribute(self, key: str, value: Any) -> None:
        """Update an attribute in self.custom_attributes if it exists.

        :param key: The attribute key to update (e.g., 'category_ids').
        :param value: The new value to set.
        """
        if hasattr(self, 'custom_attributes'):
            if key in self.custom_attributes:
                self.custom_attributes[key] = value

    def _update_attributes(self, attribute_data: dict, scope: Optional[str] = None) -> bool:
        """Sends a PUT request to update **top-level** product attributes

        .. tip:: to update attributes or custom attributes with attribute scope taken into account,
            use :meth:`~.update_attributes` or :meth:`~.update_custom_attributes` instead

        :param attribute_data: dict containing any number of top-level attributes to update
        :param scope: the scope to send the request on; will use the :attr:`.Client.scope` if not provided
        """
        url = self.data_endpoint(scope)
        payload = {
            "product": {
                "sku": self.sku
            },
            'save_options': True
        }
        payload['product'].update(attribute_data)

        response = self.client.put(url, payload)
        if response.ok:
            self.refresh(scope)
            for key in attribute_data:
                self.logger.info(
                    f"Updated {key} for {self} to {getattr(self, key)} on scope {self.get_scope_name(scope)}")
            return True
        else:
            self.logger.error(
                f'Failed with status code {response.status_code}' + '\n' +
                f'Message: {MagentoError.parse(response)}')
            return False

    def add_product_link(self, link_type: str, linked_sku: str, position: Optional[int] = None) -> bool:
        """Adds or updates a related, up-sell, or cross-sell product link.

        .. note:: If the product link already exists for the provided SKU, this method
           will only update the link if a ``position`` is specified.

        :param link_type: the product link type; must be ``upsell``, ``related`` or ``crosssell``
        :param linked_sku: the SKU of the product to be linked
        :param position: the position of the product link; if not provided, it will be added as the last link.
        :returns: boolean indicating success of the operation.
        """
        if link_type not in ('upsell', 'crosssell', 'related'):
            raise ValueError('Invalid value for `link_type` (must be "upsell", "crosssell", or "related")')

        if not (linked_product := self.client.products.by_sku(linked_sku)):
            self.logger.error(f"Invalid SKU provided: {linked_sku}")
            return False

        current_links = self.get_product_links(link_type)
        is_already_linked = linked_product.sku in [
            link['linked_product_sku']
            for link in current_links
        ]
        if position is None:
            if is_already_linked:  # Nothing to do if it's already linked and no position is specified
                self.logger.info(f'{linked_product} is already linked to {self}')
                return True

            if current_links:  # Add it as the last linked product
                position = current_links[-1]['position'] + 1
            else:
                position = 1

        url = f'{self.data_endpoint()}/links'
        product_link = {
            'link_type': link_type,
            'linked_product_sku': linked_product.sku,
            'linked_product_type': linked_product.type_id,
            'position': position,
            'sku': self.sku,
        }
        if is_already_linked:  # Update the position
            response = self.client.put(url, payload={
                'entity': product_link
            })
        else:  # Add a new product link
            response = self.client.post(url, payload={
                'items': [product_link]
            })
        if response.ok and response.json() is True:
            self.logger.info(
                f"{'Updated' if is_already_linked else 'Added'} {linked_product} "
                f"as a {link_type} product for {self}"
            )
            self.refresh()
            return True
        else:
            self.logger.error(
                f"Failed to {'update' if is_already_linked else 'add'} {linked_product} as a {link_type} product "
                f"for {self}.\nMessage: {MagentoError.parse(response)}"
            )
            return False

    def delete_product_link(self, link_type: str, linked_sku: str) -> bool:
        """Removes a related, up-sell, or cross-sell product link.

        :param link_type: the product link type; must be ``upsell``, ``related`` or ``crosssell``
        :param linked_sku: the SKU of the product link to remove
        :returns: boolean indicating success of the operation.
        """
        if link_type not in ('upsell', 'crosssell', 'related'):
            raise ValueError('Invalid value for `link_type` (must be "upsell", "crosssell", or "related")')

        url = f"{self.data_endpoint()}/links/{link_type}/{linked_sku}"
        response = self.client.delete(url)

        if response.ok and response.json() is True:
            self.logger.info(f'Deleted {linked_sku} as a {link_type} product for {self}')
            return True
        else:
            self.logger.error(
                f'Failed to delete {linked_sku} as a {link_type} product for {self}.\n'
                f'Message: {MagentoError.parse(response)}'
            )
            return False

    def get_orders(self) -> Optional[Order | List[Order]]:
        """Searches for orders that contain the product

        If the product is configurable, returns orders containing any of its child products

        :returns: orders that contain the product, as an individual or list of :class:`~.Order` objects
        """
        return self.client.orders.by_product(self)

    def get_order_items(self) -> Optional[OrderItem | List[OrderItem]]:
        """Searches for order items that contain the product

        If the product is configurable, returns order items containing any of its child products

        :returns: order items that contain the product, as an individual or list of :class:`~.OrderItem` objects
        """
        return self.client.order_items.by_product(self)

    def get_invoices(self) -> Optional[Invoice | List[Invoice]]:
        """Searches for invoices that contain the product

        If the product is configurable, returns invoices containing any of its child products

        :returns: invoices that contain the product, as an individual or list of :class:`~.Invoice` objects
        """
        return self.client.invoices.by_product(self)

    def get_customers(self) -> Optional[Customer | List[Customer]]:
        """Searches for customers that have ordered the product

        If the product is configurable, returns customers that have ordered any of its child products

        :returns: customers that have ordered the product, as an individual or list of :class:`~.Customer` objects
        """
        return self.client.customers.by_product(self)

    def get_product_links(self, link_type: str) -> List[Dict]:
        """Returns data for all product links of the specified type

        :param link_type: the product link type; must be ``upsell``, ``related`` or ``crosssell``
        """
        if link_type not in ('upsell', 'crosssell', 'related'):
            self.logger.error('Invalid link type (must be "upsell", "crosssell", or "related")')
            return []

        products = [product for product in self.product_links if product['link_type'] == link_type]
        return sorted(products, key=lambda product: product['position'])

    def get_children(self, refresh: bool = False, scope: Optional[str] = None) -> List[Product]:
        """Retrieve the child simple products of a configurable product

        :param refresh: if True, calls :meth:`~.Model.refresh` on the child products to retrieve full data
        :param scope: the scope to refresh the children on (when ``refresh=True``)
        """
        if refresh:
            for child in self.children:
                child.refresh(scope)
        return self.children

    def get_media_by_id(self, entry_id: int) -> MediaEntry:
        """Access a :class:`MediaEntry` of the product by id

        :param entry_id: the id of the media gallery entry
        """
        for entry in self.media_gallery_entries:
            if entry.id == entry_id:
                return entry


class MediaEntry(Model):
    """Wraps a media gallery entry of a :class:`Product`"""

    MEDIA_TYPES = ['base', 'small', 'thumbnail', 'swatch', 'small_image', 'image']

    DOCUMENTATION = "https://adobe-commerce.redoc.ly/2.3.7-admin/tag/productsskumediaentryId"
    IDENTIFIER = "id"
    PAYLOAD_PREFIX = 'entry'
    ALLOWED_METHODS = [ModelMethod.GET, ModelMethod.CREATE, ModelMethod.UPDATE, ModelMethod.DELETE]


    def __init__(self, product: Product, entry: dict, fetched: bool = False):
        """Initialize a MediaEntry object for a :class:`Product`

        :param product: the :class:`Product` that the gallery entry is associated with
        :param entry: the json response data to use as the source data
        """
        super().__init__(
            data=entry,
            client=product.client,
            endpoint=f'products/{product.encoded_sku}/media',
            fetched=fetched,
        )
        self.product = product

    def __repr__(self):
        return f"<MediaEntry {self.id} for {self.product}: {self.label}>"

    def save(self, add_save_options: bool = False, scope: Optional[str] = None, refresh: bool = True) -> bool:
        if not self._fetched and 'image_url' in self.data:
            self.mutable_data['image_url'] = self.data['image_url']

        if self.client.store.is_single_store:
            return super().save(add_save_options=add_save_options, refresh=refresh, multiple_scopes=[None, 'all'])

        update_scopes = [config.code for config in self.configs] + ['all']
        return super().save(add_save_options=add_save_options, refresh=refresh, update_scopes=update_scopes)

    def query_endpoint(self) -> None:
        """No search endpoint exists for media gallery entries"""
        return self.logger.info("There is no search interface for media gallery entries")

    @property
    def required_for_update_keys(self) -> List[str]:
        return ['id']

    @property
    @data_not_fetched_value(lambda self: self._media_type)
    def media_type(self) -> Optional[str]:
        return self._media_type

    @media_type.setter
    @set_private_attr_after_setter
    def media_type(self, value: Optional[str]) -> None:
        self.mutable_data['media_type'] = value

    @property
    @data_not_fetched_value(lambda self: self._label)
    def label(self) -> Optional[str]:
        return self._label

    @label.setter
    @set_private_attr_after_setter
    def label(self, value: Optional[str]) -> None:
        self.mutable_data['label'] = value

    @property
    @data_not_fetched_value(lambda self: self._position)
    def position(self) -> Optional[int]:
        return self._position

    @position.setter
    @set_private_attr_after_setter
    def position(self, value: Optional[int]) -> None:
        if not isinstance(value, int):
            raise TypeError('position must be an int')
        self.mutable_data['position'] = value

    @property
    @data_not_fetched_value(lambda self: self._disabled)
    def disabled(self) -> Optional[bool]:
        return self._disabled

    @disabled.setter
    @set_private_attr_after_setter
    def disabled(self, value: Optional[bool]) -> None:
        self.mutable_data['disabled'] = value

    @property
    @data_not_fetched_value(lambda self: self._types)
    def types(self) -> Optional[List[str]]:
        return self._types

    @types.setter
    @set_private_attr_after_setter
    def types(self, value: Optional[List[str]]) -> None:
        if not isinstance(value, list):
            raise TypeError('types must be a list')
        self.mutable_data['types'] = [t for t in value if t in self.MEDIA_TYPES]


    @property
    def is_enabled(self):
        return not self.disabled

    @property
    def is_thumbnail(self):
        return 'thumbnail' in self.types

    @cached_property
    def link(self):
        """Permalink to the image"""
        return self.client.store.active.base_media_url + 'catalog/product' + self.file

    def disable(self, scope: Optional[str] = None) -> bool:
        """Disables the MediaEntry on the given scope

        :param scope: the scope to send the request on; will use the :attr:`.Client.scope` if not provided
        """
        self.data['disabled'] = True
        return self.update(scope)

    def enable(self, scope: Optional[str] = None) -> bool:
        """Enables the MediaEntry on the given scope

        :param scope: the scope to send the request on; will use the :attr:`.Client.scope` if not provided
        """
        self.data['disabled'] = False
        return self.update(scope)

    def download(self, filename: Optional[str] = None) -> Optional[str]:
        """Downloads the MediaEntry image

        :param filename: the name of the file to save the image to; uses the filename on Magento if not provided.
        :return: the absolute path of the downloaded image file, or ``None`` if the download failed
        """
        if filename is None:
            filename = Path(self.file).name

        try:
            response = requests.get(self.link)
            response.raise_for_status()

        except requests.RequestException as e:
            self.logger.error(f"Failed to download {self}: {e}")
            return None

        fpath = Path(filename).resolve()
        with open(fpath, 'wb') as f:
            f.write(response.content)

        self.logger.info(f"Downloaded {self} to {fpath}")
        return str(fpath)

    def add_media_type(self, media_type: str, scope: Optional[str] = None) -> bool:
        """Add a media type to the MediaEntry on the given scope

        .. caution:: If the media type is already assigned to a different entry, it will be removed

        :param media_type: one of the :attr:`~.MEDIA_TYPES`
        :param scope: the scope to send the request on; will use the :attr:`.Client.scope` if not provided
        """
        if media_type in self.MEDIA_TYPES and media_type not in self.types:
            self.data['types'].append(media_type)
            return self.update(scope)

    def remove_media_type(self, media_type: str, scope: Optional[str] = None) -> bool:
        """Remove a media type from the MediaEntry on the given scope

        :param media_type: one of the :attr:`~MEDIA_TYPES`
        :param scope: the scope to send the request on; will use the :attr:`.Client.scope` if not provided
        """
        if media_type in self.types:
            self.data['types'].remove(media_type)
            return self.update(scope)

        self.logger.error(f'{media_type} is not currently assigned to {self}')
        return False

    def set_media_types(self, types: list, scope: Optional[str] = None) -> bool:
        """Set media types for the MediaEntry on the given scope

        :param types: a list containing all :attr:`~MEDIA_TYPES` to assign
        :param scope: the scope to send the request on; will use the :attr:`.Client.scope` if not provided
        """
        if not isinstance(types, list):
            raise TypeError('types must be a list')

        self.data['types'] = [t for t in types if t in self.MEDIA_TYPES]
        return self.update(scope)

    def set_position(self, position: int, scope: Optional[str] = None) -> bool:
        """Set the position of the MediaEntry on the given scope

        :param position: the position to change to
        :param scope: the scope to send the request on; will use the :attr:`.Client.scope` if not provided
        """
        if not isinstance(position, int):
            raise TypeError('position must be an int')

        self.data['position'] = position
        return self.update(scope)

    def set_alt_text(self, text: str, scope: Optional[str] = None) -> bool:
        """Set the alt text (``label``) of the MediaEntry on the given scope

        :param text: the alt text to use
        :param scope: the scope to send the request on; will use the :attr:`.Client.scope` if not provided
        """
        if not isinstance(text, str):
            raise TypeError('text must be a string')

        self.data['label'] = text
        return self.update(scope)

    def update(self, scope: Optional[str] = None) -> bool:
        """Uses the :attr:`~.data` dict to update the media entry

        .. note:: Some updates alter the data of other entries; if the update is successful, the
            associated :class:`Product` will be refreshed on the same scope to keep the data consistent

        .. tip:: If there's only 1 store view, the admin will also be updated

        :param scope: the scope to send the request on; will use the :attr:`.Client.scope` if not provided
        """
        if self.client.store.is_single_store:
            success = self._update_single_store()
        else:
            success = self._update(scope)

        self.refresh(scope)  # Get updated data if success or reset to accurate data if failed

        if success:
            self.product.refresh(scope)

        return success

    def _update_single_store(self):
        """Updates the MediaEntry data on the default store view and admin"""
        for scope in (None, 'all'):
            if not self._update(scope):
                return False  # Avoid updating admin if store update fails
        return True

    def _update(self, scope: Optional[str] = None) -> bool:
        url = self.data_endpoint(scope)
        response = self.client.put(url, payload={'entry': self.data})

        if response.ok and response.json() is True:
            self.logger.info(
                f"Updated {self} on scope {self.get_scope_name(scope)}"
            )
            return True
        else:
            self.logger.error(
                f"Failed to update {self} on scope {self.get_scope_name(scope)}"
            )
            return False


class ProductAttribute(Model):
    """Wrapper for the ``products/attributes`` endpoint"""

    DOCUMENTATION = "https://adobe-commerce.redoc.ly/2.3.7-admin/tag/productsattributes/"
    IDENTIFIER = "attribute_code"

    # Frontend input type constants
    TEXT = "text"
    TEXTAREA = "textarea"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTISELECT = "multiselect"
    PRICE = "price"
    MEDIA_IMAGE = "media_image"
    GALLERY = "gallery"

    # Allowed methods
    ALLOWED_METHODS = [ModelMethod.GET, ModelMethod.CREATE, ModelMethod.UPDATE, ModelMethod.DELETE]

    ENTITY_TYPE_ID = 4

    def __init__(self, data: dict, client: Client, fetched: bool = False):
        """Initialize a ProductAttribute object using an API response from the ``products/attributes`` endpoint

        :param data: the API response from the ``products/attributes`` endpoint
        :param client: an initialized :class:`~.Client` object
        """
        super().__init__(
            data=data,
            client=client,
            endpoint='products/attributes',
            fetched=fetched
        )

    def __repr__(self):
        return f"<Product Attribute: {self.attribute_code}>"

    # ------------------------------------------------- PROPERTIES

    @property
    def required_keys(self) -> List[str]:
        """Return the required keys for this model."""
        return []

    @property
    def mutable_keys(self) -> List[str]:
        """Return the mutable keys for this model."""
        return [
            'is_html_allowed_on_front',
            'is_visible',
            'scope',
            'is_required',
            'frontend_label',
            'note',
            'is_filterable',
            'is_filterable_in_search',
            'is_searchable',
            'is_visible_on_front',
            'is_comparable',
            'used_for_sort_by',
            'used_in_product_listing',
            'frontend_labels',
        ]

    @property
    def required_for_update_keys(self) -> List[str]:
        """Return the keys that cannot be updated."""
        return ['attribute_code', 'frontend_input', 'attribute_id']

    @property
    @data_not_fetched_value(lambda self: self._attribute_code)
    def attribute_code(self) -> Optional[bool]:
        return self._attribute_code

    @attribute_code.setter
    @set_private_attr_after_setter
    def attribute_code(self, value: Optional[bool]) -> None:
        self.mutable_data['attribute_code'] = value

    @property
    @data_not_fetched_value(lambda self: self._frontend_input)
    def frontend_input(self) -> Optional[bool]:
        return self._frontend_input

    @frontend_input.setter
    @set_private_attr_after_setter
    def frontend_input(self, value: Optional[bool]) -> None:
        self.mutable_data['frontend_input'] = value

    @property
    @data_not_fetched_value(lambda self: self._is_visible)
    def is_visible(self) -> Optional[bool]:
        return self._is_visible

    @is_visible.setter
    @set_private_attr_after_setter
    def is_visible(self, value: Optional[bool]) -> None:
        self.mutable_data['is_visible'] = value

    @property
    @data_not_fetched_value(lambda self: self._scope)
    def scope(self) -> Optional[str]:
        return self._scope

    @scope.setter
    @set_private_attr_after_setter
    def scope(self, value: Optional[str]) -> None:
        self.mutable_data['scope'] = value

    @property
    def entity_type_id(self) -> int:
        """Read-only property for entity_type_id."""
        return self.ENTITY_TYPE_ID

    @entity_type_id.setter
    def entity_type_id(self, value: Optional[int]) -> None:
        pass

    @property
    @data_not_fetched_value(lambda self: self._is_required)
    def is_required(self) -> Optional[bool]:
        return self._is_required

    @is_required.setter
    @set_private_attr_after_setter
    def is_required(self, value: Optional[bool]) -> None:
        self.mutable_data['is_required'] = value

    @property
    @data_not_fetched_value(lambda self: self._default_frontend_label)
    def default_frontend_label(self) -> Optional[str]:
        return self._default_frontend_label

    @default_frontend_label.setter
    @set_private_attr_after_setter
    def default_frontend_label(self, value: Optional[str]) -> None:
        self.mutable_data['default_frontend_label'] = value

    @property
    @data_not_fetched_value(lambda self: self._note)
    def note(self) -> Optional[str]:
        return self._note

    @note.setter
    @set_private_attr_after_setter
    def note(self, value: Optional[str]) -> None:
        self.mutable_data['note'] = value

    @property
    @data_not_fetched_value(lambda self: self._is_filterable)
    def is_filterable(self) -> Optional[bool]:
        return self._is_filterable

    @is_filterable.setter
    @set_private_attr_after_setter
    def is_filterable(self, value: Optional[bool]) -> None:
        self.mutable_data['is_filterable'] = value

    @property
    @data_not_fetched_value(lambda self: self._is_filterable_in_search)
    def is_filterable_in_search(self) -> Optional[bool]:
        return self._is_filterable_in_search

    @is_filterable_in_search.setter
    @set_private_attr_after_setter
    def is_filterable_in_search(self, value: Optional[bool]) -> None:
        self.mutable_data['is_filterable_in_search'] = value

    @property
    @data_not_fetched_value(lambda self: self._is_searchable)
    def is_searchable(self) -> Optional[bool]:
        return self._is_searchable

    @is_searchable.setter
    @set_private_attr_after_setter
    def is_searchable(self, value: Optional[bool]) -> None:
        self.mutable_data['is_searchable'] = value

    @property
    @data_not_fetched_value(lambda self: self._is_visible_on_front)
    def is_visible_on_front(self) -> Optional[bool]:
        return self._is_visible_on_front

    @is_visible_on_front.setter
    @set_private_attr_after_setter
    def is_visible_on_front(self, value: Optional[bool]) -> None:
        self.mutable_data['is_visible_on_front'] = value

    @property
    @data_not_fetched_value(lambda self: self._is_comparable)
    def is_comparable(self) -> Optional[bool]:
        return self._is_comparable

    @is_comparable.setter
    @set_private_attr_after_setter
    def is_comparable(self, value: Optional[bool]) -> None:
        self.mutable_data['is_comparable'] = value

    @property
    @data_not_fetched_value(lambda self: self._used_for_sort_by)
    def used_for_sort_by(self) -> Optional[bool]:
        return self._used_for_sort_by

    @used_for_sort_by.setter
    @set_private_attr_after_setter
    def used_for_sort_by(self, value: Optional[bool]) -> None:
        self.mutable_data['used_for_sort_by'] = value

    @property
    @data_not_fetched_value(lambda self: self._used_in_product_listing)
    def used_in_product_listing(self) -> Optional[bool]:
        return self._used_in_product_listing

    @used_in_product_listing.setter
    @set_private_attr_after_setter
    def used_in_product_listing(self, value: Optional[bool]) -> None:
        self.mutable_data['used_in_product_listing'] = value

    @property
    @data_not_fetched_value(lambda self: self._frontend_labels)
    def frontend_labels(self) -> Optional[List]:
        return self._frontend_labels

    @frontend_labels.setter
    @set_private_attr_after_setter
    def frontend_labels(self, value: Optional[List]) -> None:
        self.mutable_data['frontend_labels'] = value

    # ------------------------------------------------- CUSTOM METHODS

    @property
    def excluded_keys(self) -> List[str]:
        return ['options']

    @property
    def unpacked_options(self):
        return self.unpack_attributes(self.__options, key='label')

    @property
    def options(self) -> Optional[List[AttributeOption]]:
        return [AttributeOption(data=option, client=self.client, attribute=self, fetched=True) for option in self.__options if option['value'] != '']


class AttributeOption(Model):
    """Wrapper for the ``products/attributes/{attribute_code}/options`` endpoint"""

    DOCUMENTATION = "https://developer.adobe.com/commerce/webapi/rest/quick-reference/"
    IDENTIFIER = "value"
    ALLOWED_METHODS = [ModelMethod.GET, ModelMethod.CREATE, ModelMethod.UPDATE, ModelMethod.DELETE]

    def __init__(self,  data: dict, client: Client, attribute: ProductAttribute, fetched: bool = False):
        """Initialize an AttributeOption object for a :class:`ProductAttribute`

        :param attribute: the :class:`ProductAttribute` that the option is associated with
        :param option: the json response data to use as the source data
        """
        # we set the attribute for the api for this client
        client.product_attribute_options_attribute = attribute

        super().__init__(
            data=data,
            client=client,
            endpoint=f'products/attributes/{attribute.attribute_code}/options',
            fetched=fetched,
        )

        self.attribute = attribute

    def __repr__(self):
        return f"<AttributeOption {self.attribute.attribute_code}: {self.label}>"

    @property
    def mutable_keys(self) -> List[str]:
        return [
            'label',
            'sort_order',
            'is_default',
            'store_labels',
        ]

    @property
    def required_for_update_keys(self) -> List[str]:
        """Return the keys that cannot be updated."""
        return ['label', 'value']

    @property
    def uid(self) -> Union[str, int]:
        if self._fetched:
            return self.value

        # the only identifier we have before is created is the value
        return self.label

    @property
    def required_keys(self):
        return []

    @property
    @data_not_fetched_value(lambda self: self._label)
    def label(self) -> Optional[str]:
        return self._label

    @label.setter
    @set_private_attr_after_setter
    def label(self, value: Optional[str]) -> None:
        self.mutable_data['label'] = value

    @property
    def value(self) -> Optional[str]:
        return self._value

    @value.setter
    def value(self, val: Optional[str]) -> None:
        self._value = val

    @property
    @data_not_fetched_value(lambda self: self._sort_order)
    def sort_order(self) -> Optional[int]:
        return self._sort_order

    @sort_order.setter
    @set_private_attr_after_setter
    def sort_order(self, value: Optional[int]) -> None:
        self.mutable_data['sort_order'] = value

    @property
    @data_not_fetched_value(lambda self: self._is_default)
    def is_default(self) -> Optional[bool]:
        return self._is_default

    @is_default.setter
    @set_private_attr_after_setter
    def is_default(self, value: Optional[bool]) -> None:
        self.mutable_data['is_default'] = value

    @property
    @data_not_fetched_value(lambda self: self._store_labels)
    def store_labels(self) -> Optional[List[dict]]:
        return self._store_labels

    @store_labels.setter
    @set_private_attr_after_setter
    def store_labels(self, value: Optional[List[dict]]) -> None:
        self.mutable_data['store_labels'] = value

    def refresh(self, scope: Optional[str] = None) -> bool:
        """Updates object attributes in place using current data. Since this doesn't have a GET endpoint we need to fetch it again from the attribute"""
        self.attribute.refresh(scope=scope)

        if self._fetched:
            refreshed_data = self.client.product_attribute_options.by_id(self.uid)
        else:
            refreshed_data = self.client.product_attribute_options.by_label(self.uid)


        if refreshed_data:
            self.clear(*self.cached)
            self.set_attrs(refreshed_data.data)
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