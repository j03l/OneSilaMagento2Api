from __future__ import annotations
from typing import TYPE_CHECKING
from .manager import Manager
from ..models.sales_rule import SalesRule

if TYPE_CHECKING:
    from . import Client

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

    def get_coupons(self, rule_id: int, primary_only: bool | None = None) -> list[str]:
        """
        List all coupons for a given sales rule.
        Uses the CouponManager internally to return both specific and generated codes.

        Args:
            rule_id (int): ID of the Cart Price Rule.
            primary_only (bool | None): If True, return only the specific primary coupon; if False, only generated coupons; if None, all coupons.

        Returns:
            list[str]: coupon code strings.
        """
        return self.client.coupons.list_for_rule(rule_id, primary_only=primary_only)

    def by_name(self, name: str):
        """Retrieve sales rules by their name."""
        return self.add_criteria('name', name).execute_search()

    def active_rules(self):
        """Retrieve all active sales rules."""
        return self.add_criteria('is_active', 1).execute_search()

    def search(self, **criteria) -> list[SalesRule]:
        """
        Generic search on the sales‑rules endpoint.
        Usage: srm.search(name='10% off', coupon_code='XYZ')
        """
        original = self.endpoint
        try:
            self.endpoint = f"{original}/search"
            self.reset()
            for field, value in criteria.items():
                if value is not None:
                    self.add_criteria(field, value)
            return self.execute_search() or []
        finally:
            self.endpoint = original