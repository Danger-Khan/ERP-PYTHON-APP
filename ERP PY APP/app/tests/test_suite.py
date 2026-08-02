import unittest
import os
import json
from config import Config
from app import create_app
from app.utils.excel_db import ExcelDB
from app.models.schemas import OrderModel
from app.services.query_engine import process_query

class AtelierBackendTestCase(unittest.TestCase):

    def setUp(self):
        """Sets up test application instance and test fixtures."""
        self.app = create_app()
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        """Clean up application context."""
        self.app_context.pop()

    def test_order_balance_calculation(self):
        """Verifies order total and balance math logic."""
        order = OrderModel(
            id="ORD-999",
            invoice_number="INV-999",
            customer_id="C-001",
            customer_name="Test Customer",
            garment_type="Sherwani",
            price=15000.0,
            advance_payment=5000.0,
            discount=1000.0
        )
        record = order.to_dict()
        # Price (15000) - Discount (1000) - Advance (5000) = 9000
        self.assertEqual(record['remaining_balance'], 9000.0)

    def test_query_engine_search_and_pagination(self):
        """Verifies filtering, live search, and pagination on mock dataset."""
        dataset = [
            {"name": "Ali Khan", "city": "Peshawar", "status": "Active"},
            {"name": "Usman Ahmed", "city": "Lahore", "status": "Active"},
            {"name": "Bilal Hassan", "city": "Peshawar", "status": "Inactive"},
        ]

        # Test Search
        result = process_query(dataset, search="Peshawar")
        self.assertEqual(result['total'], 2)

        # Test Filter
        result_filtered = process_query(dataset, filters={"status": "Active"})
        self.assertEqual(result_filtered['total'], 2)

        # Test Pagination
        result_page = process_query(dataset, page=1, limit=2)
        self.assertEqual(len(result_page['data']), 2)

    def test_unauthorized_access_protection(self):
        """Verifies that protected routes reject unauthorized requests."""
        response = self.client.get('/api/customers/')
        self.assertEqual(response.status_code, 401)

if __name__ == '__main__':
    unittest.main()