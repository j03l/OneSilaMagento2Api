import unittest
from tests.mixins import TestModelMixin
from dotenv import load_dotenv
import os

class TestShipmentModel(TestModelMixin, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        load_dotenv()

        # Fetch an order item associated with the default order
        item = cls.api.order_items.add_order_id_criteria(os.getenv('DEFAULT_ORDER_ID')).execute_search()

        # Handle both single and multiple items
        if isinstance(item, list):
            cls.items = item
        else:
            cls.items = [item]

        # Create a shipment
        cls.shipment = cls.api.shipments.create_shipment(
            order=cls.items[0].order,
            items=cls.items,
            quantities=[1],
            data={}
        )

        # Track number to be used in the tests
        cls.track_number = '123123'

    def test_create_track(self):
        # Test creating a track for the shipment
        result = self.shipment.create_track(
            carrier_code='dhl',
            title='DHL',
            track_number=self.track_number,
            description='Yoyo'
        )

        # Refresh the shipment to confirm the track was added
        self.shipment.refresh()

        # Assertions
        self.assertTrue(result, "Failed to create the track.")
        track_exists = any(track.track_number == self.track_number for track in self.shipment.tracks)
        self.assertTrue(track_exists, "Track was not created successfully.")

    def test_create_comment(self):
        # Test creating a comment for the shipment
        result = self.shipment.create_comment(
            comment='Nice comment',
            is_visible_on_front=False,
            is_customer_notified=False
        )

        # Refresh the shipment to confirm the comment was added
        self.shipment.refresh()

        # Assertions
        self.assertTrue(result, "Failed to create the comment.")
        comment_exists = any(comment.comment == 'Nice comment' for comment in self.shipment.comments)
        self.assertTrue(comment_exists, "Comment was not created successfully.")

    def test_delete_track_by_track_number(self):
        result = self.shipment.delete_track_by_track_number(self.track_number)

        # Refresh the shipment to confirm the track was deleted
        self.shipment.refresh()

        # Assertions
        self.assertTrue(result, "Failed to delete the track by track number.")
        track_still_exists = any(track.track_number == self.track_number for track in self.shipment.tracks)
        self.assertFalse(track_still_exists, "Track was not deleted.")

if __name__ == '__main__':
    unittest.main()