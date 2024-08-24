from __future__ import annotations

from functools import cached_property

from . import FetchedOnlyModel, APIResponse, ImmutableModel
from typing import TYPE_CHECKING, Optional, List

from ..constants import ModelMethod

if TYPE_CHECKING:
    from magento import Client
    from . import Order, OrderItem

class Shipment(FetchedOnlyModel, ImmutableModel):
    """A model representing a shipment, with methods to interact with shipment-specific API endpoints."""

    DOCUMENTATION = "https://adobe-commerce.redoc.ly/2.3.7-admin/tag/shipment"
    IDENTIFIER = "entity_id"
    PAYLOAD_PREFIX = 'entity'
    ALLOWED_METHODS = [ModelMethod.GET, ModelMethod.DELETE] # the create is custom and have no real update


    def __init__(self, data: dict, client: Client, fetched: bool = False):
        super().__init__(data=data, client=client, endpoint='shipment', list_endpoint='shipments' ,fetched=fetched)

    def __repr__(self):
        return f"<Magento Shipment of order {self.increment_id} (qty: {self.total_qty})>"

    @property
    def excluded_keys(self):
        return ['tracks', 'comments', 'items', 'packages']

    @cached_property
    def tracks(self) -> List[APIResponse]:
        """The tracks of the shipmment in a APIResponse class"""
        return [APIResponse(data=data, endpoint=f"{self.endpoint}/track", client=self.client, fetched=True) for data in self.__tracks]

    @cached_property
    def comments(self) -> List[APIResponse]:
        """The comments of the shipmment in a APIResponse class"""
        return [APIResponse(data=data, endpoint=f"{self.data_endpoint()}/comments", client=self.client, fetched=True) for data in self.__comments]

    @cached_property
    def items(self) -> List[APIResponse]:
        """The items of the shipmment in a APIResponse class. No endpoint"""
        return [APIResponse(data=data, endpoint="", client=self.client, fetched=True) for data in self.__items]

    @cached_property
    def packages(self) -> List[APIResponse]:
        """The tracks of the shipmment in a APIResponse class. No endpoint"""
        return [APIResponse(data=data, endpoint="", client=self.client, fetched=True) for data in self.__packages]

    def create_track(self, carrier_code: str, title: str, track_number: str, description: str = "", qty: Optional[int] = None, weight: Optional[float] = None) -> bool:
        """Create a tracking number for the shipment."""
        if qty is None:
            qty = sum(item.qty for item in self.items)
        if weight is None:
            weight = sum(item.weight for item in self.items)

        payload = {
            "entity": {
                "carrier_code": carrier_code,
                "title": title,
                "track_number": track_number,
                "description": description,
                "order_id": self.order_id,
                "parent_id": self.uid,
                "qty": qty,
                "weight": weight
            }
        }

        url = self.client.url_for(f"{self.endpoint}/track")
        response = self.client.post(url, payload)
        return response.ok

    def delete_track(self, track_id: int) -> bool:
        """Delete a tracking number from the shipment."""
        url = self.client.url_for(f"{self.endpoint}/track/{track_id}")
        response = self.client.delete(url)
        return response.ok

    def delete_track_by_track_number(self, track_number: str) -> bool:
        """Delete a tracking number from the shipment by its track number."""
        track_to_delete = next((track for track in self.tracks if str(track.track_number) == track_number), None)
        if track_to_delete:
            return self.delete_track(track_to_delete.entity_id)
        return False

    def create_comment(self, comment: str, is_visible_on_front: bool = False, is_customer_notified: bool = False) -> bool:
        """Create a comment for the shipment."""
        payload = {
            "entity": {
                "comment": comment,
                "is_visible_on_front": int(is_visible_on_front),
                "is_customer_notified": int(is_customer_notified),
                "parent_id": self.uid,
            }
        }
        url = f"{self.data_endpoint()}/comments"
        response = self.client.post(url, payload)
        return response.ok

    def get_comments(self) -> List[APIResponse]:
        self.refresh()
        return self.comments

    def send_email(self) -> bool:
        """Send an email for the shipment."""
        url = self.client.url_for(f"{self.data_endpoint()}/emails")
        response = self.client.post(url, payload={})
        return response.ok

    def get_label(self) -> Optional[str]:
        """Get the label for the shipment."""
        url = self.client.url_for(f"shipments/{self.uid}/label")
        response = self.client.get(url)
        if response.ok:
            return response.json()
        return None
