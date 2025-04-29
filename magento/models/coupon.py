from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from magento import Client

from . import ImmutableModel


class Coupon(ImmutableModel):
    """Wrapper for the ``coupons`` endpoint.
    Wraps a single coupon code resource.

    :param data: API response from the ``coupons`` endpoint
    :param client: an initialized :class:`~.Client` object
    """

    DOCUMENTATION = "https://adobe-commerce.redoc.ly/2.4.8-admin/tag/coupons"
    IDENTIFIER = "coupon_id"
    PAYLOAD_PREFIX = 'coupon'
   

    def __init__(self, data: Dict, client: Client, fetched: bool = False):
        """Initialize a Coupon object using an API response from the ``coupons`` endpoint

        :param data: API response from the ``coupons`` endpoint
        :param client: an initialized :class:`~.Client` object
        """
        super().__init__(data=data, client=client, endpoint="coupons", fetched=fetched)

    def __repr__(self):
        return f"<Magento Coupon: {self.code}>"

    def get_rule(self):
        """Retrieve the cart price rule associated with this coupon"""
        return self.client.rules.by_id(self.rule_id)

    @property
    def remaining_uses(self) -> Optional[int]:
        """Number of uses remaining before reaching usage_limit."""
        if self.usage_limit is None:
            return None
        return max(self.usage_limit - self.times_used, 0)

    @property
    def is_exhausted(self) -> bool:
        """Whether the coupon has reached its usage limit."""
        if self.usage_limit is None:
            return False
        return self.times_used >= self.usage_limit

    @property
    def is_expired(self) -> bool:
        """Whether the coupon is expired."""
        if not self.expiration_date:
            return False
        from datetime import datetime, timezone

        exp = datetime.fromisoformat(self.expiration_date)
        return exp < datetime.now(timezone.utc)

    @property
    def days_remaining(self) -> Optional[int]:
        """Number of days until expiration (None if no expiration_date)."""
        if not self.expiration_date:
            return None
        from datetime import datetime, timezone

        exp = datetime.fromisoformat(self.expiration_date)
        delta = exp - datetime.now(timezone.utc)
        return max(delta.days, 0)

    @property
    def rule(self):
        """Cart price rule associated with this coupon."""
        return self.get_rule()
