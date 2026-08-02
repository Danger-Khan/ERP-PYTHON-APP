from datetime import datetime
from app.utils.excel_db import ExcelDB

class AnalyticsEngine:

    @staticmethod
    def get_dashboard_summary() -> dict:
        orders_db = ExcelDB('orders')
        inventory_db = ExcelDB('inventory')
        employees_db = ExcelDB('employees')

        orders = orders_db.get_all()
        inventory = inventory_db.get_all()
        employees = employees_db.get_all()

        today_str = datetime.now().strftime("%Y-%m-%d")

        # 1. Order Status Counts
        status_counts = {"Pending": 0, "In Progress": 0, "Ready": 0, "Delivered": 0, "Cancelled": 0}
        overdue_orders = []
        today_deliveries = []

        for o in orders:
            status = o.get('status', 'Pending')
            if status in status_counts:
                status_counts[status] += 1

            # Check Overdue & Delivery Schedules
            del_date = str(o.get('delivery_date', ''))
            if del_date:
                if del_date < today_str and status not in ['Delivered', 'Cancelled']:
                    overdue_orders.append(o)
                elif del_date == today_str and status not in ['Delivered', 'Cancelled']:
                    today_deliveries.append(o)

        # 2. Inventory Alerts
        low_stock_count = sum(
            1 for item in inventory 
            if float(item.get('stock_quantity', 0)) <= float(item.get('min_stock_alert', 10))
        )

        # 3. Tailor Workload Allocation
        tailor_workload = {}
        for emp in employees:
            if emp.get('status') == 'On Duty':
                emp_name = emp.get('name')
                assigned = sum(1 for o in orders if o.get('assigned_tailor') == emp_name and o.get('status') in ['Pending', 'In Progress'])
                tailor_workload[emp_name] = assigned

        return {
            "order_stats": status_counts,
            "total_orders": len(orders),
            "overdue_count": len(overdue_orders),
            "due_today_count": len(today_deliveries),
            "low_stock_alerts": low_stock_count,
            "active_tailor_workload": tailor_workload,
            "overdue_orders": overdue_orders[:5]  # Top 5 urgent
        }