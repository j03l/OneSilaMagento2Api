from __future__ import annotations
from typing import TYPE_CHECKING
from .manager import Manager
from ..models.coupon import Coupon

if TYPE_CHECKING:
    from . import Client

class CouponManager(Manager):
    def __init__(self, client: Client):
        """Initialize a :class:`CustomerManager`

        :param client: an initialized :class:`~.Client` object
        """
        super().__init__(
            endpoint='coupons',
            client=client,
            model=Coupon
        )

    def list_for_rule(self, rule_id: int, primary_only: bool|None = None) -> list[Coupon]:
        """
        Lists generated coupons for a rule.
        If primary_only=True, returns only the manually assigned code.
        """
        self.endpoint = f"{self.endpoint}/search"

        self.reset()

        self.add_criteria('rule_id', rule_id)
        if primary_only is not None:
            self.add_criteria('is_primary', int(primary_only))

        return self.execute_search()

    def generate(self,
                 rule_id: int,
                 qty: int,
                 length: int,
                 prefix: str = '',
                 suffix: str = '',
                 dash_every_x_chars: int | None = None,
                 fmt: str = 'ALPHANUMERIC'
    ) -> list[str]:
        """
        Auto-generates new coupon codes.
        """
        payload = {
            "generationSpec": {
                "rule_id": rule_id,
                "qty": qty,
                "length": length,
                "format": fmt,
                "prefix": prefix,
                "suffix": suffix,
                "dash_every_x_chars": dash_every_x_chars
            }
        }
        url = self.client.url_for(f"{self.endpoint}/generate")
        response = self.client.post(url, payload)
        return response.json()

    def create_specific_coupon(self, rule_id: int, coupon_code: str) -> Coupon:
        """
        Creates a specific coupon for a given sales rule.

        Args:
            rule_id (int): The ID of the sales rule.
            coupon_code (str): The specific coupon code to create.

        Returns:
            Coupon: The created coupon object.
        """
        payload = {
            "rule_id": rule_id,
            "code": coupon_code,
            "is_primary": True
        }
        url = self.client.url_for(self.endpoint)
        response = self.client.post(url, payload)
        return self.Model(response.json())

    def update_specific_coupon(self, coupon_id: int, updates: dict) -> Coupon:
        """
        Updates a specific coupon by its ID.

        Args:
            coupon_id (int): The ID of the coupon to update.
            updates (dict): A dictionary of fields to update (e.g., {'code': 'NEWCODE2025'}).

        Returns:
            Coupon: The updated coupon object.
        """
        url = self.client.url_for(f"{self.endpoint}/{coupon_id}")
        response = self.client.put(url, updates)
        return self.Model(response.json())

    def delete_coupon(self, coupon_id: int) -> bool:
        """
        Deletes a coupon by its ID.

        Args:
            coupon_id (int): The ID of the coupon to delete.

        Returns:
            bool: True if the deletion was successful, False otherwise.
        """
        url = self.client.url_for(f"{self.endpoint}/{coupon_id}")
        response = self.client.delete(url)
        return response.status_code == 200


    def list_codes_for_rule(self, rule_id: int, primary_only: bool | None = None) -> list[str]:
        """Return just the coupon code strings for a given rule.

        Args:
            rule_id (int): ID of the Cart Price Rule.
            primary_only (bool | None): 
                - True: only the manually assigned coupon
                - False: only generated coupons
                - None: all coupons

        Returns:
            list[str]: coupon code strings.
        """
        return [c.code for c in self.list_for_rule(rule_id, primary_only=primary_only)]
