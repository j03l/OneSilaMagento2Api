from __future__ import annotations
from typing import TYPE_CHECKING, List, Union, Dict, Optional
from datetime import datetime, timedelta, timezone
from .manager import Manager
from ..models.coupon import Coupon

if TYPE_CHECKING:
    from . import Client

class CouponManager(Manager):
    def __init__(self, client: Client):
        """Initialize a :class:`CouponManager`

        :param client: an initialized :class:`~.Client` object
        """
        super().__init__(
            endpoint='coupons',
            client=client,
            model=Coupon
        )
        
    def search(self, **criteria) -> List[Coupon]:
        """
        Generic search on the coupons endpoint.
        Usage: cm.search(code='ABC123', rule_id=10)
        """
        original = self.endpoint
        try:
            self.endpoint = f"{original}/search"
            self.reset()
            for field, value in criteria.items():
                if value is not None:
                    self.add_criteria(field, value)
            results = self.execute_search() or []
            
            # Handle case where API returns single object instead of list
            if not results:
                return []
            elif isinstance(results, list):
                return results
            else:
                return [results]
        finally:
            self.endpoint = original


    def list_for_rule(self, rule_id: int, primary_only: Optional[bool] = None) -> List[Coupon]:
        """List all coupons for a given sales rule.

        Args:
            rule_id (int): ID of the Cart Price Rule.
            primary_only (bool | None): 
                - True: only the specific manually assigned coupon
                - False: only generated coupons
                - None: all coupons
        Returns:
            List[Coupon]: list of Coupon objects.
        """
        criteria = {'rule_id': rule_id}
        if primary_only is not None:
            criteria['is_primary'] = int(primary_only)
        results = self.search(**criteria)
        
        # Handle case where API returns single object instead of list
        if not results:
            return []
        elif isinstance(results, list):
            return results
        else:
            return [results]
    
    def generate(self,
                 rule_id: int,
                 qty: int,
                 length: int,
                 prefix: str = '',
                 suffix: str = '',
                 dash_every_x_chars: Optional[int] = None,
                 fmt: str = 'ALPHANUMERIC'
    ) -> List[str]:
        """
        Auto-generates new coupon codes for a given sales rule.
        """
        payload = {
            "couponSpec": {
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
        return self.Model(response.json(), self.client)

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
        return self.Model(response.json(), self.client)

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


    def by_code(self, code: str) -> Optional[Coupon]:
        """Retrieve a coupon by its code.

        Args:
            code (str): The coupon code.

        Returns:
            Optional[Coupon]: The coupon object if found, None otherwise.
        """
        results = self.search(code=code)
        if not results:
            return None
        # The search method already handles the case where API returns single object
        # and always returns a list, so we can safely access the first element
        return results[0] if results else None

    def by_codes(self, codes: List[str]) -> List[Coupon]:
        """Retrieve multiple coupons by their codes.

        Args:
            codes (List[str]): List of coupon codes.

        Returns:
            List[Coupon]: List of coupon objects found.
        """
        if not codes:
            return []
        
        # Since we can't search by multiple codes in one query, we need to search each
        # This could be optimized in the future with a custom endpoint
        coupons = []
        for code in codes:
            if coupon := self.by_code(code):
                coupons.append(coupon)
        return coupons

    def list_codes_for_rule(self, rule_id: int, primary_only: Optional[bool] = None) -> List[str]:
        """Return just the coupon code strings for a given rule.

        Args:
            rule_id (int): ID of the Cart Price Rule.
            primary_only (bool | None): 
                - True: only the manually assigned coupon
                - False: only generated coupons
                - None: all coupons

        Returns:
            List[str]: coupon code strings.
        """
        return [c.code for c in self.list_for_rule(rule_id, primary_only=primary_only)]

    def delete_by_codes(self, coupon_codes: List[str]) -> bool:
        """Bulk delete coupons by their codes.

        Args:
            coupon_codes (List[str]): List of coupon codes to delete.

        Returns:
            bool: True if deletion was successful.
        """
        payload = {"couponCodes": coupon_codes}
        url = self.client.url_for(f"{self.endpoint}/deleteByCodes")
        response = self.client.post(url, payload)
        return response.status_code == 200

    def delete_by_ids(self, coupon_ids: List[int]) -> bool:
        """Bulk delete coupons by their IDs.

        Args:
            coupon_ids (List[int]): List of coupon IDs to delete.

        Returns:
            bool: True if deletion was successful.
        """
        payload = {"couponIds": coupon_ids}
        url = self.client.url_for(f"{self.endpoint}/deleteByIds")
        response = self.client.post(url, payload)
        return response.status_code == 200

    def active_coupons(self) -> List[Coupon]:
        """Retrieve all active (non-expired, non-exhausted) coupons.

        Returns:
            List[Coupon]: List of active coupon objects.
        """
        all_coupons = self.search()
        if not all_coupons:
            return []
        
        return [c for c in all_coupons if not c.is_expired and not c.is_exhausted]

    def expired_coupons(self) -> List[Coupon]:
        """Retrieve all expired coupons.

        Returns:
            List[Coupon]: List of expired coupon objects.
        """
        all_coupons = self.search()
        if not all_coupons:
            return []
        
        return [c for c in all_coupons if c.is_expired]

    def exhausted_coupons(self) -> List[Coupon]:
        """Retrieve coupons that have reached their usage limit.

        Returns:
            List[Coupon]: List of exhausted coupon objects.
        """
        all_coupons = self.search()
        if not all_coupons:
            return []
        
        return [c for c in all_coupons if c.is_exhausted]

    def expiring_soon(self, days: int = 7) -> List[Coupon]:
        """Retrieve coupons expiring within the specified number of days.

        Args:
            days (int): Number of days to look ahead. Defaults to 7.

        Returns:
            List[Coupon]: List of coupons expiring soon.
        """
        all_coupons = self.search()
        if not all_coupons:
            return []
        
        cutoff_date = datetime.now(timezone.utc) + timedelta(days=days)
        expiring_coupons = []
        
        for coupon in all_coupons:
            if coupon.expiration_date:
                try:
                    exp_date = datetime.fromisoformat(coupon.expiration_date)
                    
                    # Ensure expiration date is timezone-aware for consistent comparison
                    if exp_date.tzinfo is None:
                        exp_date = exp_date.replace(tzinfo=timezone.utc)
                        
                    if exp_date <= cutoff_date and not coupon.is_expired:
                        expiring_coupons.append(coupon)
                except (ValueError, TypeError):
                    # Skip coupons with invalid date formats
                    continue
        
        return expiring_coupons

    def created_between(self, start_date: str, end_date: str) -> List[Coupon]:
        """Retrieve coupons created between two dates.

        Args:
            start_date (str): Start date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).
            end_date (str): End date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).

        Returns:
            List[Coupon]: List of coupons created in the date range.
        """
        all_coupons = self.search()
        if not all_coupons:
            return []
        
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            
            # Ensure both dates are timezone-aware for consistent comparisons
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
                
        except (ValueError, TypeError):
            raise ValueError("Invalid date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
        
        filtered_coupons = []
        for coupon in all_coupons:
            if coupon.created_at:
                try:
                    created = datetime.fromisoformat(coupon.created_at)
                    
                    # Ensure created date is timezone-aware for consistent comparison
                    if created.tzinfo is None:
                        created = created.replace(tzinfo=timezone.utc)
                        
                    if start <= created <= end:
                        filtered_coupons.append(coupon)
                except (ValueError, TypeError):
                    # Skip coupons with invalid date formats
                    continue
        
        return filtered_coupons

    def most_used(self, limit: int = 10) -> List[Coupon]:
        """Retrieve the most frequently used coupons.

        Args:
            limit (int): Maximum number of coupons to return. Defaults to 10.

        Returns:
            List[Coupon]: List of most used coupons, sorted by usage count.
        """
        all_coupons = self.search()
        if not all_coupons:
            return []
        
        # Sort by times_used in descending order
        sorted_coupons = sorted(all_coupons, key=lambda c: c.times_used or 0, reverse=True)
        return sorted_coupons[:limit]

    def unused(self) -> List[Coupon]:
        """Retrieve coupons that have never been used.

        Returns:
            List[Coupon]: List of unused coupon objects.
        """
        all_coupons = self.search()
        if not all_coupons:
            return []
        
        return [c for c in all_coupons if (c.times_used or 0) == 0]

    def by_usage_range(self, min_uses: int, max_uses: int) -> List[Coupon]:
        """Retrieve coupons within a specific usage range.

        Args:
            min_uses (int): Minimum number of uses (inclusive).
            max_uses (int): Maximum number of uses (inclusive).

        Returns:
            List[Coupon]: List of coupons within the usage range.
        """
        all_coupons = self.search()
        if not all_coupons:
            return []
        
        return [
            c for c in all_coupons 
            if min_uses <= (c.times_used or 0) <= max_uses
        ]

    def usage_statistics(self, rule_id: Optional[int] = None) -> Dict[str, Union[int, float]]:
        """Get usage statistics for coupons.

        Args:
            rule_id (Optional[int]): If provided, statistics for coupons of this rule only.

        Returns:
            Dict[str, Union[int, float]]: Dictionary with usage statistics.
        """
        if rule_id:
            coupons = self.list_for_rule(rule_id)
        else:
            coupons = self.search()
        
        if not coupons:
            return {
                "total_coupons": 0,
                "total_uses": 0,
                "unused_coupons": 0,
                "average_uses": 0.0,
                "max_uses": 0,
                "min_uses": 0
            }
        
        uses = [c.times_used or 0 for c in coupons]
        total_uses = sum(uses)
        unused_count = sum(1 for use in uses if use == 0)
        
        return {
            "total_coupons": len(coupons),
            "total_uses": total_uses,
            "unused_coupons": unused_count,
            "average_uses": total_uses / len(coupons) if coupons else 0.0,
            "max_uses": max(uses) if uses else 0,
            "min_uses": min(uses) if uses else 0
        }

    def count(self) -> int:
        """Return the total number of coupons.

        Returns:
            int: Total number of coupons.
        """
        # Use search with pageSize=1 to get total_count efficiently
        original = self.endpoint
        try:
            self.endpoint = f"{original}/search"
            self.reset()
            query = f"{self.query}searchCriteria[pageSize]=1&fields=total_count"
            response = self.client.get(query)
            return response.json().get('total_count', 0)
        finally:
            self.endpoint = original

    def count_by_rule(self, rule_id: int) -> int:
        """Return the number of coupons for a specific rule.

        Args:
            rule_id (int): ID of the sales rule.

        Returns:
            int: Number of coupons for the rule.
        """
        return len(self.list_for_rule(rule_id))

    def get_default_get_method(self, identifier: str) -> Optional[Coupon]:
        """Override the default get method to retrieve a coupon by code instead of ID.

        Args:
            identifier (str): The coupon code.

        Returns:
            Optional[Coupon]: The coupon object if found, None otherwise.
        """
        return self.by_code(identifier)

    def get_or_create(
        self,
        identifier: str,
        data: dict,
        scope: Optional[str] = None,
    ) -> Coupon:
        """Retrieve an existing coupon by code, or create a new one if not found.

        Args:
            identifier (str): The coupon code.
            data (dict): Attributes to set on the coupon if it needs to be created.
            scope (Optional[str]): Optional scope for the request.

        Returns:
            Coupon: The retrieved or newly created Coupon instance.
        """
        # Try to retrieve the existing coupon by code
        coupon = self.by_code(identifier)

        if coupon:
            self.client.logger.info(f'Coupon with code: {identifier} found.')
            return coupon

        # If not found, create a new coupon with the provided code
        self.client.logger.info(f'Coupon with code: {identifier} not found. Creating new coupon.')
        # Ensure the code is included in the data
        if 'code' not in data:
            data['code'] = identifier
        return self.create(data=data, scope=scope)

    def all_in_memory(self) -> List[Coupon]:
        """Fetch all coupons across all pages.
        
        Override to use the correct search endpoint for pagination.
        """
        original_endpoint = self.endpoint
        original_query = self.query
        try:
            self.endpoint = f"{original_endpoint}/search"
            self.query = self.client.url_for(self.endpoint) + '/?'
            return super().all_in_memory()
        finally:
            self.endpoint = original_endpoint
            self.query = original_query
    