from services.order_card_service import CUST_HEADERS, ORD_HEADERS
from excel_manager import ExcelManager, clean_val

em = ExcelManager()
customers = em.read_records("customers.xlsx", CUST_HEADERS)
orders = em.read_records("orders.xlsx", ORD_HEADERS)

print("CUST_HEADERS:", CUST_HEADERS)
print("Customers sample:")
for r in customers[:3]:
    print({h: clean_val(r.get(h, "")) for h in CUST_HEADERS})

print("ORD_HEADERS:", ORD_HEADERS)
print("Orders sample:")
for r in orders[:3]:
    print({h: clean_val(r.get(h, "")) for h in ORD_HEADERS})
