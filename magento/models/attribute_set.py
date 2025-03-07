from __future__ import annotations
from . import Model, Product, APIResponse, ProductAttribute
from typing import TYPE_CHECKING, Optional, List
from ..constants import ModelMethod
from ..decorators import set_private_attr_after_setter
from ..exceptions import LockedAttributeError, GeneralApiError, GroupNotFoundError

if TYPE_CHECKING:
    from magento import Client

class AttributeSet(Model):
    """Wrapper for the ``attribute-sets`` endpoint"""

    DOCUMENTATION = 'https://adobe-commerce.redoc.ly/2.3.7-admin/tag/attribute-sets/'
    IDENTIFIER = 'attribute_set_id'
    ALLOWED_METHODS = [ModelMethod.GET, ModelMethod.CREATE, ModelMethod.UPDATE, ModelMethod.DELETE]
    ENTITY_TYPE_ID = 4

    def __init__(self, data: dict, client: Client, fetched: bool = False):
        """Initialize an AttributeSet object using an API response from the ``attribute-sets`` endpoint

        :param data: the API response from the ``attribute-sets`` endpoint
        :param client: an initialized :class:`~.Client` object
        """
        super().__init__(
            data=data,
            client=client,
            fetched=fetched,
            endpoint='products/attribute-sets',
        )
        self.mutable_data['entity_type_id'] = self.ENTITY_TYPE_ID

    def __repr__(self):
        return f"<Magento AttributeSet: {self.attribute_set_name}>"

    # ------------------------------------------------- PROPERTIES

    @property
    def required_for_update_keys(self) -> List[str]:
        """Keys required for update operations."""
        return ['attribute_set_id', 'attribute_set_name', 'entity_type_id']

    @property
    def attribute_set_name(self) -> Optional[str]:
        return self._attribute_set_name

    @property
    def sort_order(self) -> Optional[int]:
        return self._sort_order

    @property
    def entity_type_id(self) -> int:
        """Read-only property for entity_type_id."""
        return self.ENTITY_TYPE_ID

    @property
    def skeleton_id(self) -> Optional[int]:
        return self._skeleton_id

    # ------------------------------------------------- PROPERTIES SETTERS

    @attribute_set_name.setter
    @set_private_attr_after_setter
    def attribute_set_name(self, value: Optional[str]) -> None:
        self.mutable_data['attribute_set_name'] = value

    @sort_order.setter
    @set_private_attr_after_setter
    def sort_order(self, value: Optional[int]) -> None:
        self.mutable_data['sort_order'] = value

    @entity_type_id.setter
    @set_private_attr_after_setter
    def entity_type_id(self, value: Optional[int]) -> None:
        self.mutable_data['entity_type_id'] = value

    @skeleton_id.setter
    @set_private_attr_after_setter
    def skeleton_id(self, value: Optional[int]) -> None:
        # this will only be added on create
        if not self._fetched:
            self.mutable_data['skeleton_id'] = value

    def get_products(self) -> Optional[List[Product]]:
        """Retrieve all products associated with this attribute set."""
        return self.client.products.by_attribute_set(self)

    # ------------------------------------------------- CUSTOM METHODS
    def get_or_create_group_by_name(self, attribute_group_name: str) -> Model:
        if not self._fetched:
            raise ValueError('The attribute set is not created.')

        try:
            return self.get_group_by_name(attribute_group_name)
        except GroupNotFoundError:
            return self.create_group(attribute_group_name)

    def create_group(self, attribute_group_name: str) -> Model:
        """Create a new attribute group within this attribute set."""
        if not self._fetched:
            raise ValueError('The attribute set is not created.')

        payload = {
            "group": {
                "attributeGroupName": attribute_group_name,
                "attributeSetId": self.attribute_set_id,
            }
        }

        endpoint = f'{self.endpoint}/groups'
        response = self.client.post(self.client.url_for(endpoint), payload)

        if not response.ok:
            raise ValueError(f"Failed to create attribute group '{attribute_group_name}': {response.text}")

        return Model(data=response.json(), client=self.client, endpoint=endpoint, fetched=True)

    def update_group_name(self, attribute_group_id: int, new_name: str) -> Model:
        """Update the name of an attribute group within this attribute set."""
        if not self._fetched:
            raise ValueError('The attribute set is not created.')

        payload = {
            "group": {
                "attribute_group_id": attribute_group_id,
                "attribute_group_name": new_name,
                "attribute_set_id": self.attribute_set_id,
            }
        }

        endpoint = f'{self.endpoint}/{self.attribute_set_id}/groups'
        response = self.client.put(self.client.url_for(endpoint), payload)
        return Model(data=response.json(), client=self.client, endpoint=endpoint, fetched=True)

    def delete_group(self, attribute_group_id: int) -> bool:
        """Delete an attribute group from this attribute set."""
        if not self._fetched:
            raise ValueError('The attribute set is not created.')

        response = self.client.delete(self.client.url_for(f'{self.endpoint}/groups/{attribute_group_id}'))
        return response.ok

    def get_group_by_name(self, attribute_group_name: str) -> Model:
        """Get a group within this attribute set by name."""
        if not self._fetched:
            raise ValueError('The attribute set is not created.')

        groups = self.get_groups()
        for group in groups:
            if group.attribute_group_name == attribute_group_name:
                return group

        raise GroupNotFoundError(attribute_group_name)

    def get_groups(self)-> Optional[APIResponse | List[APIResponse]]:
        if not self._fetched:
            raise ValueError('The attribute set is not created.')

        return self.client.manager(f'{self.endpoint}/groups/list').add_criteria('attribute_set_id', self.attribute_set_id).execute_search()

    def add_attribute_set_attribute(self, attribute_group_id: int, attribute_code: str, sort_order: int) -> bool:
        """Add an attribute to a group within this attribute set."""
        if not self._fetched:
            raise ValueError('The attribute set is not created.')

        # Check if the attribute already exists in the attribute set
        endpoint = f'{self.endpoint}/attributes'
        existing_attributes = self.get_attributes()
        for attr in existing_attributes:
            if attr.attribute_code == attribute_code:
                self.logger.debug(f"Attribute {attribute_code} already exists in attribute set {self.attribute_set_id}.")
                return True

        # If the attribute doesn't exist, then add it
        payload = {
            'attributeSetId': self.attribute_set_id,
            'attributeGroupId': attribute_group_id,
            'attributeCode': attribute_code,
            'sortOrder': sort_order,
        }
        response = self.client.post(self.client.url_for(endpoint), payload)
        return response.ok

    def update_attribute_sort_orders(self, attribute_group_id: int, sort_order_dict: dict) -> bool:
        """
        Update sort orders for existing attributes in this attribute set.
        :param attribute_group_id: The attribute group ID.
        :param sort_order_dict: Dictionary with attribute_code as key and new sort order as value.
        :return: True if all updates succeed, False otherwise.
        """
        success = True
        for attribute_code, sort_order in sort_order_dict.items():
            endpoint = f'{self.endpoint}/{self.attribute_set_id}/attributes/{attribute_code}'
            payload = {
                'attributeGroupId': attribute_group_id,
                'attributeCode': attribute_code,
                'sortOrder': sort_order,
            }
            response = self.client.put(self.client.url_for(endpoint), payload)
            if not response.ok:
                self.logger.error(
                    f"Failed to update sort order for attribute {attribute_code} with status code {response.status_code}."
                )
                success = False

        return success

    def remove_attribute_set_attribute(self, attribute_code: str) -> bool:
        """Remove an attribute from this attribute set."""
        if not self._fetched:
            raise ValueError('The attribute set is not created.')

        url = self.client.url_for(f'{self.endpoint}/{self.attribute_set_id}/attributes/{attribute_code}')
        response = self.client.delete(url)

        if response.ok:
            return True

        content = response.content.decode('utf-8')
        error_message = (
            f"Failed to remove attribute {attribute_code} from attribute set {self.attribute_set_id} with status code {response.status_code}.\n"
            f"Message: {content}"
        )
        self.logger.error(error_message)

        if 'does not exist' in content:
            if self.client.strict_mode:
                raise AttributeError(f"Attribute set attribute with code {attribute_code} does not exist!")
        elif 'is locked' in content:
            if self.client.strict_mode:
                raise LockedAttributeError(f"Attribute set attribute with code {attribute_code} is locked!")
        else:
            if self.client.strict_mode:
                raise GeneralApiError(error_message)

        return False

    def get_attributes(self) -> List[ProductAttribute]:
        """Retrieve related attributes based on the attribute set ID."""
        if not self._fetched:
            raise ValueError('The attribute set is not created.')

        endpoint = f'{self.endpoint}/{self.attribute_set_id}/attributes'
        response = self.client.get(self.client.url_for(endpoint))
        return [ProductAttribute(data=data, client=self.client, fetched=True) for data in response.json() ]