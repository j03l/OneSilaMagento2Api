from typing import TYPE_CHECKING
from .manager import Manager
from ..models.sales_rule import SalesRule

if TYPE_CHECKING:
    from magento import Client

class SalesRuleManager(Manager):
    def __init__(self, client: Client):
        """Initialize a :class:`SalesRuleManager`

        :param client: an initialized :class:`~.Client` object
        """
        super().__init__(
            endpoint='salesRules',
            client=client,
            model=SalesRule
        )

    def get_specific_coupon(self, rule_id: int) -> str | None:
        """
        Fetches the single “Specific Coupon” code defined on this rule,
        or None if the rule uses auto-generation.
        """
        rule = self.by_id(rule_id)
        # coupon_type == 2 indicates Specific Coupon
        return rule.coupon_code if getattr(rule, 'coupon_type', None) == 2 else None

    def by_name(self, name: str):
        """Retrieve sales rules by their name."""
        return self.add_criteria('name', name).execute_search()

    def active_rules(self):
        """Retrieve all active sales rules."""
        return self.add_criteria('is_active', 1).execute_search()

    def by_coupon_code(self, coupon_code: str):
        """Retrieve sales rules associated with a specific coupon code."""
        return self.add_criteria('coupon_code', coupon_code).execute_search()