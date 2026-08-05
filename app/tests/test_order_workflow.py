"""Regression tests for the separated customer registration and order flow."""
import unittest

from app.services import order_card_service as svc


class FakeExcelManager:
    def __init__(self):
        self.written = {}

    def read_records(self, filename, headers):
        return []

    def write_all_records(self, filename, headers, rows):
        self.written[filename] = {"headers": headers, "rows": rows}


class ExistingCustomerOrderTestCase(unittest.TestCase):
    def setUp(self):
        self.manager = FakeExcelManager()
        self.customers = [{"id": "C-101", "name": "Ayesha Khan", "phone": "03001234567"}]
        self.form = {
            "name": "Ayesha Khan", "phone": "03001234567", "date": "2026-08-05",
            "garments": ["Kameez"], "status": "Pending", "tailor": "Ali",
            "delivery_status": "Not Delivered", "total": "2500", "advance": "500",
        }

    def test_existing_customer_order_does_not_write_customer_sheet(self):
        customer_id, order_id = svc.save_order_for_customer(
            self.manager, self.customers, [], self.form, "C-101")

        self.assertEqual((customer_id, order_id), ("C-101", "ORD-101"))
        self.assertNotIn("customers.xlsx", self.manager.written)
        self.assertEqual(self.manager.written["orders.xlsx"]["rows"][0][1], "Ayesha Khan")
        self.assertIn("measurements.xlsx", self.manager.written)
        self.assertIn("styles.xlsx", self.manager.written)

    def test_unknown_customer_cannot_receive_an_order(self):
        with self.assertRaisesRegex(ValueError, "Select an existing customer"):
            svc.save_order_for_customer(self.manager, self.customers, [], self.form, "C-999")


if __name__ == "__main__":
    unittest.main()
