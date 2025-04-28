from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import Coupon, CouponSpec
from .manager import Manager

if TYPE_CHECKING:
    from . import Client


class CouponManager(Manager):
    """:class:`ManagerQuery` subclass for the ``coupons/search`` endpoint"""

    def __init__(self, client: Client):
        """Initialize a :class:`CouponManager`

        :param client: an initialized :class:`~.Client` object
        """
        super().__init__(endpoint="coupons/search", client=client, model=Coupon)

    def by_id(self, coupon_id: int) -> Coupon:
        """
        Retrieve a coupon by its ID.

        :param coupon_id: The coupon’s unique ID.
        :returns: The fetched :class:`Coupon`.
        """
        self.query = self.query.replace("coupons/search", "coupons")
        return super().by_id(coupon_id)

    def generate(self, spec: CouponSpec) -> list[str]:
        """
        Auto-generate coupon codes.

        :param spec: A :class:`CouponSpec` instance with generation parameters.
        :returns: A list of generated coupon code strings.
        """
        url = self.client.url_for("coupons/generate")
        payload = {"couponSpec": spec.model_dump()}
        response = self.client.post(url, json=payload)
        return response.json()

    def create(self, data: dict[str, object]) -> Coupon:
        """
        Create a specific coupon code.

        :param data: Fields for the new coupon,
            e.g. {"rule_id": ..., "code": "...", ...}.
        :returns: The created :class:`Coupon` object.
        :raises ApiError: On HTTP error or validation failure.
        """
        endpoint = self.endpoint.replace("/search", "")
        url = self.client.url_for(endpoint)
        resp = self.client.post(url, json={"coupon": data})
        return Coupon(**resp.json())

    def update(self, coupon_id: int, data: dict[str, object]) -> Coupon:
        """
        Update an existing coupon.

        :param coupon_id: ID of the coupon to update.
        :param data: Fields to modify.
        :returns: The updated :class:`Coupon`.
        """
        endpoint = self.endpoint.replace("/search", "")
        url = self.client.url_for(f"{endpoint}/{coupon_id}")
        resp = self.client.put(url, json={"coupon": data})
        return Coupon(**resp.json())

    def delete(self, coupon_id: int) -> None:
        """
        Delete a coupon by ID.

        :param coupon_id: The coupon’s ID.
        """
        endpoint = self.endpoint.replace("/search", "")
        url = self.client.url_for(f"{endpoint}/{coupon_id}")
        self.client.delete(url)

    def search(self, **search_criteria) -> list[Coupon]:
        """
        Search for coupons matching criteria.

        :param search_criteria: Keyword search criteria (see Magento SearchCriteria format).
        :returns: A list of :class:`Coupon` objects.
        """
        resp = self.client.get(
            self.client.url_for(self.endpoint), params=search_criteria
        )
        items = resp.json().get("items", [])
        return [Coupon(**item) for item in items]
