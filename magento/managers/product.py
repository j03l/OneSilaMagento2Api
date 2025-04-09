from __future__ import annotations

import base64
from typing import Union, Iterable, List, Optional, TYPE_CHECKING

import requests

from .manager import Manager, MinimalManager
from ..models import Model, APIResponse, Product, Category, ProductAttribute, MediaEntry
from ..models.attribute_set import AttributeSet
from ..models.product import AttributeOption
from ..utils import mime_type

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

    def by_attribute_set(self, attribute_set: AttributeSet) -> Optional[List[Product]]:
        """Retrieve all :class:`~.Product`s associated with a given :class:`~.AttributeSet`

        :param attribute_set: the attribute set instance to filter products by
        :returns: a list of :class:`~.Product` objects associated with the attribute set
        """
        return self.add_criteria(
            field='attribute_set_id',
            value=attribute_set.attribute_set_id
        ).execute_search()

    def get_media(self, product: Product, media_id) -> Optional[MediaEntry]:
        url = self.client.url_for(f"products/{product.encoded_sku}/media/{media_id}")

        response = self.client.get(url=url)
        if response.ok:
            return MediaEntry(product=product, entry=response.json(), fetched=True)

        return  None

    def create(self, data: dict, scope: Optional[str] = None, extra_data: Optional[dict] = None) -> Optional[Model]:
        # Modify extra_data before calling super().create
        if extra_data and 'custom_attributes' in extra_data:
            attribute_data = extra_data['custom_attributes']
            # Pack the attributes using self.model
            extra_data['custom_attributes'] = self.Model.pack_attributes(attribute_data)

        # Call the original create method with the modified extra_data
        return super().create(data=data, scope=scope, extra_data=extra_data)

    def count(self) -> int:
        """Return the total number of ProductAttributes"""
        # Build query manually
        query = f"{self.query}searchCriteria[pageSize]=1&fields=total_count"
        response = self.client.get(query)
        return response.json().get('total_count', 0)

class MediaEntryManager(MinimalManager):
    """
    :class:`MinimalManager` subclass for managing media entries in the ``products/{product_sku}/media`` endpoint.

    This manager handles retrieving, creating, and managing media entries for a specific product.
    """

    def __init__(self, client: Client, product: Product):
        """Initialize a :class:`MediaEntryManager`

        :param product: The :class:`Product` instance to which the media entries belong.
        """
        # Initialize the MinimalManager with the appropriate endpoint and model
        super().__init__(
            endpoint=f"products/{product.encoded_sku}/media",
            client=client,
            model=MediaEntry
        )
        self.product = product

    def __repr__(self):
        return f"<MediaEntryManager for {self.product.sku}>"

    def create(self, data: dict, scope: Optional[str] = None) -> Optional[MediaEntry]:
        """
        Create a media entry for the current product.
        If in a multi-store setup, re-save to apply fields across scopes properly.
        """
        # First, create the entry
        instance = super().create(data=data, scope=scope)

        # Extra step: in multi-store mode, save again to ensure scoped fields are persisted
        if instance and not self.client.store.is_single_store:
            instance.save(refresh=True)

        return instance

    def by_id(self, media_id: int) -> Optional[MediaEntry]:
        """Retrieve a MediaEntry by its ID.

        :param media_id: The ID of the media entry.
        """
        return self.client.products.get_media(product=self.product, media_id=media_id)

    def all(self) -> List[MediaEntry]:
        """Retrieve all media entries for the Product."""
        return self.product.media_gallery_entries

    def get_instance_for_create(self, data) -> Model:
        """
        Method to get the instance to be created. It allows override so we don't need to override the whole create.

        :param data: The dict instance containing attributes for the new instance.
        :return: A new MediaEntry instance.
        """
        # Handle the image processing logic
        image_url = data.pop('image_url')
        if not image_url:
            raise ValueError("Image URL must be provided when creating a new media entry.")

        filename = image_url.split('/')[-1]
        if image_url.startswith('http'):
            img_content = requests.get(image_url).content
        else:
            with open(image_url, 'rb') as f:
                img_content = f.read()

        instance = MediaEntry(entry=data,  product=self.product, fetched=False)

        instance.mutable_data['content'] = {
            "base64_encoded_data": base64.b64encode(img_content).decode('utf-8'),
            "type": mime_type(filename),
            "name": filename
        }

        return instance


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
        self.add_criteria('position', 0, 'gteq')
        return super().all_in_memory()

    def by_code(self, attribute_code: str) -> Optional[ProductAttribute]:
        """Retrieve a :class:`~.ProductAttribute` by its attribute code

        :param attribute_code: the code of the :class:`~.ProductAttribute`
        """
        return self.by_id(attribute_code)

    def get_types(self) -> Optional[List[APIResponse]]:
        """Retrieve a list of all available :class:`~.ProductAttribute` types"""
        return self.client.manager(f'{self.endpoint}/types').execute_search()




class ProductAttributeOptionManager(MinimalManager):
    """
    :class:`MinimalManager` subclass for managing attribute options in the ``products/attributes/{attribute_code}/options`` endpoint.

    https://github.com/magento/magento2/issues/26374
    For some reason the api for options will only give value and label. Will not give the sort_order and the store_labels. They say is not a bug
    And you need to have the store code scope in order to get all. Honestly I think the peroson that replyied didn't understand the issue so
    for now we will update these fields 'blindly' (with no way to know if they are really updated).

    By just looking into the admin frotnend it seems to work.

    """

    def __init__(self, client: Client, attribute: ProductAttribute):
        """Initialize a :class:`ProductAttributeOptionManager`

        :param attribute: The :class:`ProductAttribute` instance to which the options belong.
        """
        # Initialize the MinimalManager with the appropriate endpoint and model
        super().__init__(
            endpoint=f"products/attributes/{attribute.attribute_code}/options",
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

    def by_id(self, id: str | int) -> Optional[AttributeOption]:
        """Retrieve an AttributeOption by its label.

        :param label: The label of the option.
        """
        self.attribute.refresh()
        for option in self.attribute.options:
            if int(option.value) == int(id):
                return option
        self.client.logger.info(f"No option found with label: {id} for {self.attribute}")
        return None

    def all(self) -> List[AttributeOption]:
        """Retrieve all options for the ProductAttribute."""
        return self.attribute.options

    def get_default_get_method(self, identifier: str) -> Optional[AttributeOption]:
        """Override the default get method to retrieve an option by label."""
        return self.by_label(identifier)

    def get_instance_for_create(self, data) -> Model:
        """
        Override the parent one
        """
        return AttributeOption(data=data, client=self.client, attribute=self.attribute)