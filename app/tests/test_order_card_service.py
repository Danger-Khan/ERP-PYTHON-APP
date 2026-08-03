import unittest
from app.services import order_card_service as svc


class FakeExcelMgr:
    def __init__(self):
        self.written = {}

    def write_all_records(self, filename, headers, rows):
        self.written[filename] = {
            "headers": headers,
            "rows": rows,
        }

    def read_records(self, filename, headers):
        return []


class OrderCardServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.form = {
            "name": "Test Customer",
            "phone": "03001234567",
            "date": "2026-08-03",
            "address": "123 Test St",
            "garments": ["Kameez", "Shalwar"],
            "lambai": "40",
            "chest": "38",
            "waist": "34",
            "hip": "42",
            "shoulder": "15",
            "sleeve": "22",
            "collar": "16",
            "cuff": "8",
            "armhole": "20",
            "tera": "0",
            "pocket": "0",
            "shalwar_length": "38",
            "bottom": "18",
            "paancha": "10",
            "daman": "20",
            "button_style": "Baz Button",
            "collar_style": "Normal",
            "cuff_style": "Round Cuff",
            "pocket_style": "One",
            "daman_style": "Round Daman",
            "stitching": "1. Single Stitch",
            "sleeve_type": "Full",
            "shalwar_type": "Normal",
            "status": "Pending",
            "tailor": "Ali",
            "notes": "Sample note",
            "delivery_date": "2026-08-10",
            "delivery_time": "10:00",
            "delivered_by": "Tailor Ali",
            "delivery_status": "Not Delivered",
            "total": "2000",
            "advance": "500",
        }

    def test_clean_num_handles_invalid_values(self):
        self.assertEqual(svc.clean_num(""), 0.0)
        self.assertEqual(svc.clean_num(None), 0.0)
        self.assertEqual(svc.clean_num("1,200.50"), 1200.5)
        self.assertEqual(svc.clean_num("abc"), 0.0)

    def test_next_id_generates_sequential_id(self):
        records = [{"id": "C-101"}, {"id": "C-102"}, {"id": "ORD-150"}]
        self.assertEqual(svc.next_id(records, "C", 101), "C-103")
        self.assertEqual(svc.next_id(records, "ORD", 101), "ORD-151")
        self.assertEqual(svc.next_id([], "C", 101), "C-101")

    def test_compute_remaining_never_negative(self):
        self.assertEqual(svc.compute_remaining("2000", "500"), 1500.0)
        self.assertEqual(svc.compute_remaining("2000", "2500"), 0.0)

    def test_validate_detects_missing_fields_and_advance_errors(self):
        empty = {"name": "", "phone": "", "date": "", "garments": [], "total": "100", "advance": "200"}
        errors = svc.validate(empty)
        self.assertIn("Customer name is required.", errors)
        self.assertIn("Mobile number is required.", errors)
        self.assertIn("Date is required.", errors)
        self.assertIn("Select at least one garment type.", errors)
        self.assertIn("Advance paid cannot exceed the total amount.", errors)

    def test_order_row_maps_style_fields_correctly(self):
        row = svc.order_row(self.form, "ORD-110", "C-110", "Test Customer")
        self.assertEqual(row["button_style"], "Baz Button")
        self.assertEqual(row["daman_style"], "Round Daman")
        self.assertEqual(row["stitching"], "1. Single Stitch")
        self.assertEqual(row["total"], "2000.00")
        self.assertEqual(row["advance"], "500.00")
        self.assertEqual(row["remaining"], "1500.00")

    def test_build_receipt_text_includes_style_lines(self):
        receipt = svc.build_receipt_text(self.form, "C-110", "ORD-110")
        self.assertIn("Button : Baz Button", receipt)
        self.assertIn("Daman : Round Daman", receipt)
        self.assertIn("Stitch : 1. Single Stitch", receipt)

    def test_save_order_writes_all_excel_sheets(self):
        fake_mgr = FakeExcelMgr()
        customer_id, order_id = svc.save_order(fake_mgr, [], [], self.form)
        self.assertEqual(customer_id, "C-101")
        self.assertEqual(order_id, "ORD-101")
        self.assertIn("customers.xlsx", fake_mgr.written)
        self.assertIn("orders.xlsx", fake_mgr.written)
        self.assertIn("measurements.xlsx", fake_mgr.written)
        self.assertIn("styles.xlsx", fake_mgr.written)
        self.assertEqual(fake_mgr.written["orders.xlsx"]["rows"][0][0], "ORD-101")


if __name__ == "__main__":
    unittest.main()
