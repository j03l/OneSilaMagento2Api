from __future__ import annotations
from typing import Union, Iterable, List, Optional, TYPE_CHECKING
from magento.managers import Manager
from ..models import Model, TaxClass
from ..exceptions import InstanceGetFailed, MagentoError

if TYPE_CHECKING:
    from . import Client

class TaxClassManager(Manager):
    """
    Manager for the taxClasses endpoint.

    Provides methods to create, retrieve, update, delete, and search TaxClass instances.
    """

    def __init__(self, client: Client):
        super().__init__(endpoint='taxClasses/search', create_endpoint='taxClasses', client=client, model=TaxClass)

    def by_id(self, class_id: int) -> Optional[Model]:

        # the search url is different from the GET one
        self.query =self.client.url_for('taxClasses') + '/' + str(class_id)
        instance =  self.execute_search(apply_pagination=False)

        if self.client.strict_mode and instance is None:
            error_message = f"{self.Model} with uid {class_id} does not exists!"
            self.client.logger.error(error_message)

            raise InstanceGetFailed(error_message)

        return instance

    def validate_result(self) -> Optional[Dict | List[Dict]]:
        """Parses the response and returns the actual result data, regardless of search approach"""

        if not self._result:
            return None

        if isinstance(self._result, list):
            return self._result

        if self._result.get('message'):  # Error; logged by Client
            return None

        # this needed to be overrided because our get only 2 fields
        if len(self._result.keys()) > 2 and 'items' not in self._result:  # Single item, retrieved by id
            return self._result

        if 'items' in self._result:  # All successful responses with search criteria have `items` key
            items = self._result['items']
            if items:  # Response can still be {'items': None} though
                if len(items) > 1:
                    return items
                return items[0]
            else:
                self.client.logger.info(
                    "No matching {} for this search query".format(self.endpoint)
                )
                return None
        # I have no idea what could've gone wrong, sorry :/
        msg = "Manager failed with an unknown error.\nAPI Response: {}".format(self._result)
        raise MagentoError(self.client, msg)