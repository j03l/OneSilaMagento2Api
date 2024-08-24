import unittest
from magento.models import Order
from tests.mixins import TestModelMixin
from dotenv import load_dotenv
import os

class TestOrderModel(TestModelMixin, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        load_dotenv()

        # Retrieve an existing order by its ID from the environment variable
        order_id = os.getenv('DEFAULT_ORDER_ID')
        cls.order = cls.api.orders.by_id(order_id)
        cls.order.refresh()

        cls.assertIsNotNone(cls.order, "Failed to fetch the order for testing.")

    def test_update_order_status_to_processing(self):
        # Test updating the order status to 'processing'
        result = self.order.update_status(status=Order.STATUS_PROCESSING, comment="Processing the order")
        self.order.refresh()
        self.assertEqual(self.order.status, Order.STATUS_PROCESSING)


    def test_hold_order(self):
        # Test holding the order
        result = self.order.update_status(status=Order.STATUS_HOLDED)
        self.order.refresh()
        self.assertEqual(self.order.status, Order.STATUS_HOLDED)

    def test_unhold_order(self):
        # Test unholding the order
        #We first need to hold it to test unhold
        hold_result = self.order.update_status(status=Order.STATUS_UNHOLDED)
        result = self.order.update_status(status=Order.STATUS_PROCESSING, comment="Processing the order")
        self.order.refresh()
        self.order.refresh()
        self.assertEqual(self.order.status, Order.STATUS_PROCESSING)

    # the following tests can't been performed or it will block the order
    # def test_cancel_order(self):
    #     # Test canceling the order
    #     result = self.order.update_status(status=Order.STATUS_CANCELED)
    #     self.order.refresh()
    #     self.assertEqual(self.order.status, Order.STATUS_CANCELED)

    # def test_update_order_status_with_comment(self):
    #     # Test updating the order status with a comment and notification
    #     result = self.order.update_status(status=Order.STATUS_COMPLETE, comment="Order completed")
    #     self.order.refresh()
    #     self.assertEqual(self.order.status, Order.STATUS_COMPLETE)


if __name__ == '__main__':
    unittest.main()
