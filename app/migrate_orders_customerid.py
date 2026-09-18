from services.order_card_service import ORD_HEADERS
from excel_manager import ExcelManager, clean_val

em = ExcelManager()
# Read current customers and orders
cust_headers = ['id','name','phone','length','sleeve','shoulder','collar','chest','waist','daman','shalwar_len','paancha','address','created_date']
customers = em.read_records('customers.xlsx', cust_headers)
orders = em.read_records('orders.xlsx', ORD_HEADERS)

name_to_id = {clean_val(c.get('name')): clean_val(c.get('id')) for c in customers if c.get('id')}

changed = False
for o in orders:
    # prefer customer_id field
    cid = clean_val(o.get('customer_id') or '')
    if cid and cid.startswith('C-'):
        continue
    # try candidate from customer or customer_id
    candidate = clean_val(o.get('customer') or o.get('customer_id') or '')
    if not candidate:
        continue
    # if candidate is a name that maps to id
    mapped = name_to_id.get(candidate)
    if mapped:
        if o.get('customer_id') != mapped:
            o['customer_id'] = mapped
            changed = True
    else:
        # if candidate looks like C- already leave it
        if candidate.startswith('C-'):
            o['customer_id'] = candidate
            changed = True
        else:
            # leave as-is (maybe external customer) but store in customer_id for consistency
            o['customer_id'] = candidate
            changed = True

if changed:
    # write back using ORD_HEADERS order
    rows = [[clean_val(o.get(h)) for h in ORD_HEADERS] for o in orders]
    em.write_all_records('orders.xlsx', ORD_HEADERS, rows)
    print('orders.xlsx migrated; wrote', len(rows), 'rows')
else:
    print('No migration needed')

# print sample
print('Sample orders:')
for o in orders[:5]:
    print({h: clean_val(o.get(h,'')) for h in ORD_HEADERS})
