from datetime import datetime

class OrderModel:
    """Data model representing a customer tailoring order."""
    def __init__(self, id=None, invoice_number=None, customer_id=None, customer_name="",
                 garment_type="", price=0.0, advance_payment=0.0, discount=0.0,
                 remaining_balance=None, order_date=None, delivery_date=None,
                 status="Pending", assigned_tailor="", priority="Normal",
                 measurements_snapshot="", notes=""):
        self.id = id
        self.invoice_number = invoice_number
        self.customer_id = customer_id
        self.customer_name = customer_name
        self.garment_type = garment_type
        self.price = float(price)
        self.advance_payment = float(advance_payment)
        self.discount = float(discount)

        # Automatically calculate balance if not provided
        if remaining_balance is None:
            self.remaining_balance = max(0.0, (self.price - self.discount) - self.advance_payment)
        else:
            self.remaining_balance = float(remaining_balance)

        self.order_date = order_date or datetime.now().strftime("%Y-%m-%d")
        self.delivery_date = delivery_date or datetime.now().strftime("%Y-%m-%d")
        self.status = status
        self.assigned_tailor = assigned_tailor
        self.priority = priority
        self.measurements_snapshot = measurements_snapshot
        self.notes = notes

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "garment_type": self.garment_type,
            "price": self.price,
            "advance_payment": self.advance_payment,
            "discount": self.discount,
            "remaining_balance": self.remaining_balance,
            "order_date": self.order_date,
            "delivery_date": self.delivery_date,
            "status": self.status,
            "assigned_tailor": self.assigned_tailor,
            "priority": self.priority,
            "measurements_snapshot": self.measurements_snapshot,
            "notes": self.notes
        }


class CustomerModel:
    """Data model for customer measurement and profile records."""
    def __init__(self, id=None, name="", phone="", chest="", waist="", length="", sleeves="", created_at=None):
        self.id = id
        self.name = name
        self.phone = phone
        self.chest = chest
        self.waist = waist
        self.length = length
        self.sleeves = sleeves
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "chest": self.chest,
            "waist": self.waist,
            "length": self.length,
            "sleeves": self.sleeves,
            "created_at": self.created_at
        }


class InventoryItemModel:
    """Data model for fabric and item inventory."""
    def __init__(self, id=None, item_code=None, item_name="", stock_quantity=0.0, min_stock_alert=10.0,
                 unit="Meters", category="Fabric", unit_cost=0.0, selling_price=0.0, supplier=""):
        self.id = id
        self.item_code = item_code or id
        self.item_name = item_name
        self.stock_quantity = float(stock_quantity)
        self.min_stock_alert = float(min_stock_alert)
        self.unit = unit
        self.category = category
        self.unit_cost = float(unit_cost)
        self.selling_price = float(selling_price)
        self.supplier = supplier

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "item_code": self.item_code,
            "item_name": self.item_name,
            "stock_quantity": self.stock_quantity,
            "min_stock_alert": self.min_stock_alert,
            "unit": self.unit,
            "category": self.category,
            "unit_cost": self.unit_cost,
            "selling_price": self.selling_price,
            "supplier": self.supplier
        }

# Alias for compatibility
InventoryModel = InventoryItemModel


class EmployeeModel:
    """Data model for shop tailors and staff."""
    def __init__(self, id=None, name="", role="Tailor", status="On Duty", phone="",
                 salary=0.0, cnic="", current_task="None", specialization="General"):
        self.id = id
        self.name = name
        self.role = role
        self.status = status
        self.phone = phone
        self.salary = float(salary)
        self.cnic = cnic
        self.current_task = current_task
        self.specialization = specialization

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "status": self.status,
            "phone": self.phone,
            "salary": self.salary,
            "cnic": self.cnic,
            "current_task": self.current_task,
            "specialization": self.specialization
        }