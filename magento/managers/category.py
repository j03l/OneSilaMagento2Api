from __future__ import annotations
from typing import Union, Iterable, List, Optional, TYPE_CHECKING
from .manager import Manager
from ..models import Category

if TYPE_CHECKING:
    from . import Client


class CategoryManager(Manager):

    """:class:`ManagerQuery` subclass for the ``categories`` endpoint"""

    def __init__(self, client: Client):
        """Initialize a :class:`CategoryManager`

        :param client: an initialized :class:`~.Client` object
        """
        super().__init__(
            endpoint='categories',
            client=client,
            model=Category
        )

    def by_id(self, item_id: Union[int, str]) -> Optional[Category]:
        self.query += f'rootCategoryId={item_id}'
        return self.execute_search(apply_pagination=False)

    def by_list(self, field: str, values: Iterable) -> Optional[Category, List[Category]]:
        self.query = self.query.replace('categories', 'categories/list')
        return super().by_list(field, values)

    def get_root(self) -> Category:
        """Retrieve the top level/default :class:`~.Category` (every other category is a subcategory)"""
        return self.execute_search()

    def all(self) -> List[Category]:
        """Retrieve a list of all categories"""
        self.query = self.query.replace('categories', 'categories/list') + 'searchCriteria[currentPage]=1'
        return self.execute_search()

    def by_name(self, name: str, exact: bool = True) -> Optional[Category | List[Category]]:
        """Manager for a :class:`~.Category` by name

        :param name: the category name to search for
        :param exact: whether the name should be an exact match
        """
        self.query = self.query.replace('categories', 'categories/list')
        if exact:
            return self.add_criteria('name', name).execute_search()
        else:
            return self.add_criteria('name', f'%25{name}%25', 'like').execute_search()
