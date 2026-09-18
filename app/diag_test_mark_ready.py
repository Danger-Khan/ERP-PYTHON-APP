from services.order_card_service import ORD_HEADERS
from excel_manager import ExcelManager, clean_val

em = ExcelManager()
orders = em.read_records("orders.xlsx", ORD_HEADERS)
if not orders:
    print("No orders found")
    raise SystemExit(0)

# pick the first order as target
target = orders[0]
order_id = target.get('id')
print('Target order:', order_id)

# mark it ready
for o in orders:
    if o.get('id') == order_id:
        o['status'] = 'Ready'

rows = [[o.get(h, '') for h in ORD_HEADERS] for o in orders]
em.write_all_records('orders.xlsx', ORD_HEADERS, rows)

# re-read and show result
orders2 = em.read_records('orders.xlsx', ORD_HEADERS)
print('After update sample:')
for o in orders2[:3]:
    print({h: clean_val(o.get(h, '')) for h in ORD_HEADERS})
