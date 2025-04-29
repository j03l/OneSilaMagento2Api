from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from magento import Client
    
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
        return getattr(self, 'is_active', False)

    @property
    def coupon_type(self) -> str:
        """Returns the type of coupon associated with the sales rule."""
        return getattr(self, 'coupon_type', 'Unknown')

    def get_coupons(self):
        """Retrieve all coupons associated with this sales rule."""
        return self.client.coupons.list_for_rule(self.rule_id)