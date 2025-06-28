from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from magento import Client
    from magento.models.coupon import Coupon

from . import ImmutableModel

class SalesRule(ImmutableModel):
    """Wraps a Cart Price Rule (salesRules) response."""
    IDENTIFIER = 'rule_id'
    PAYLOAD_PREFIX = 'rule'
    mutable_fields = {
        # include fields you’ll PATCH/PUT, e.g. name, is_active, coupon_type, use_auto_generation, etc.
    }

    def __init__(self, data: dict, client: Client, fetched: bool = False):
        """Initialize a SalesRule object using an API response from the ``salesRules`` endpoint

        :param data: API response from the ``salesRules`` endpoint
        :param client: an initialized :class:`~.Client` object
        """
        super().__init__(data=data, client=client, endpoint="salesRules", fetched=fetched)

    @property
    def is_active(self) -> bool:
        """Indicates whether the sales rule is active."""
        return getattr(self, '_is_active', False)

    @is_active.setter
    def is_active(self, value):
        """Set the is_active status."""
        self._is_active = bool(value)

    @property
    def coupon_type(self) -> str:
        """Returns the type of coupon associated with the sales rule."""
        return getattr(self, '_coupon_type', 'Unknown')

    @coupon_type.setter
    def coupon_type(self, value):
        """Set the coupon type."""
        self._coupon_type = str(value)

    def get_coupons(self, primary_only: Optional[bool] = None) -> List['Coupon']:
        """List coupon objects for this rule.

        Args:
            primary_only (Optional[bool]):
                - True: only the specific manually assigned coupon
                - False: only generated coupons
                - None: all coupons

        Returns:
            List[Coupon]: the coupon objects.
        """
        return self.client.coupons.list_for_rule(self.id, primary_only=primary_only)
