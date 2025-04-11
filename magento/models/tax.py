from typing import List, Optional
from magento.models import Model
from magento.constants import ModelMethod
from magento.decorators import data_not_fetched_value, set_private_attr_after_setter


class TaxClass(Model):
    """
    Wrapper for the taxClasses endpoint.

    API Documentation:
      - POST /V1/taxClasses: Create a Tax Class.
      - PUT /V1/taxClasses/{classId}: Update a Tax Class.
      - GET /V1/taxClasses/{taxClassId}: Retrieve a Tax Class.
      - DELETE /V1/taxClasses/{taxClassId}: Delete a Tax Class.

    Fields:
      - class_id (int): The tax class ID (used as the unique identifier).
      - class_name (str): Required. The tax class name (this field is mutable).
      - class_type (str): Required. The tax class type (for example, "PRODUCT" or "CUSTOMER").

    Note: On creation both class_name and class_type are required.
          For updates, only class_name may be changed, while class_type and class_id remain required.
    """

    DOCUMENTATION = "https://your.documentation.link/taxClasses"  # Update with the real URL if available.
    IDENTIFIER = "class_id"
    ALLOWED_METHODS = [ModelMethod.GET, ModelMethod.CREATE, ModelMethod.UPDATE, ModelMethod.DELETE]
    PAYLOAD_PREFIX = 'taxClass'
    CLASS_TYPE_PRODUCT = 'PRODUCT'
    CLASS_TYPE_CUSTOMER = 'CUSTOMER'

    def __init__(self, data: dict, client, fetched: bool = False):
        super().__init__(data=data, client=client, endpoint='taxClasses', fetched=fetched)

    def __repr__(self):
        return f"<TaxClass: {self.class_id} - {self.class_name}>"

    # ------------------------------------------------- PROPERTIES

    @property
    def required_keys(self) -> List[str]:
        # Both class_name and class_type are required for creation.
        return ['class_name', 'class_type']

    @property
    def mutable_keys(self) -> List[str]:
        # Only class_name can be updated after creation.
        return ['class_name']

    @property
    def required_for_update_keys(self) -> List[str]:
        # When updating, class_id and class_type must be present in the payload.
        return ['class_id', 'class_type']

    @property
    @data_not_fetched_value(lambda self: self._class_id)
    def class_id(self) -> Optional[int]:
        return self._class_id

    @class_id.setter
    @set_private_attr_after_setter
    def class_id(self, value: Optional[int]) -> None:
        self.mutable_data['class_id'] = value

    @property
    @data_not_fetched_value(lambda self: self._class_name)
    def class_name(self) -> Optional[str]:
        return self._class_name

    @class_name.setter
    @set_private_attr_after_setter
    def class_name(self, value: Optional[str]) -> None:
        self.mutable_data['class_name'] = value

    @property
    @data_not_fetched_value(lambda self: self._class_type)
    def class_type(self) -> Optional[str]:
        return self._class_type

    @class_type.setter
    @set_private_attr_after_setter
    def class_type(self, value: Optional[str]) -> None:
        self.mutable_data['class_type'] = value