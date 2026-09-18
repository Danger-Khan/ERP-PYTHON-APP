"""Business logic for the digital garment order card (digitized JTQ slip).

All persistence goes through the project ExcelManager so the desktop GUI and
the Flask API share one code path.
"""
from datetime import datetime

# ---------------------------------------------------------------------------
# Constants (single source of truth for both GUI and API)
# ---------------------------------------------------------------------------

GARMENT_OPTIONS = ["Kameez", "Shalwar", "Coat", "Waistcoat", "Pant", "Shirt", "Others"]

# (field key, display label) — keeps the paper-form arrangement familiar
MEASUREMENT_FIELDS = [
    ("lambai", "Lambai (Length)"),
    ("chest", "Chest"),
    ("waist", "Waist"),
    ("hip", "Hip"),
    ("shoulder", "Shoulder"),
    ("sleeve", "Sleeve"),
    ("collar", "Collar"),
    ("cuff", "Cuff"),
    ("armhole", "Armhole"),
    ("tera", "Tera"),
    ("pocket", "Pocket"),
    ("shalwar_length", "Shalwar Length"),
    ("bottom", "Bottom"),
    ("paancha", "Paancha"),
    ("daman", "Daman"),
]

STYLE_GROUPS = {
    "button_style": ("Button Style", ["Baz Button", "Karh Button", "Normal", "None"]),
    "collar_style": ("Collar Type", ["Normal", "Chinese", "Sherwani", "Round"]),
    "cuff_style": ("Cuff Type", ["Round Cuff", "Square Cuff", "Normal", "None"]),
    "pocket_style": ("Pocket Type", ["One", "Two", "Hidden", "None"]),
    "daman_style": ("Daman Type", ["Square Daman", "Round Daman", "Normal", "None"]),
    "stitching": ("Stitching", ["1. Single Stitch", "2. Double Stitch", "3. Choka Stitch", "4. Triple Stitch"]),
    "sleeve_type": ("Sleeve Style", ["Full", "Half", "Short", "None"]),
    "shalwar_type": ("Shalwar Style", ["Normal", "Churidar", "Patiala", "Simple"]),
}

ORDER_STATUSES = ["Pending", "In Progress", "Ready", "Delivered"]
DELIVERY_STATUSES = ["Not Delivered", "Delivered", "Partial"]

# Legacy columns kept first so existing .xlsx rows keep positional compatibility;
# new columns are appended at the END (same strategy as the ORD button_style column).
CUST_HEADERS = [
    "id", "name", "phone", "length", "sleeve", "shoulder", "collar", "chest",
    "waist", "daman", "shalwar_len", "paancha", "address", "created_date",
]

ORD_HEADERS = [
    "id", "customer_id", "garment", "status", "tailor", "collar_style", "cuff_style",
    "pocket_style", "daman_style", "stitching", "button_style",
    # new order-card fields
    "order_date", "delivery_date", "delivery_time", "delivered_by",
    "delivery_status", "notes", "total", "advance", "remaining",
]

MEAS_HEADERS = ["order_id"] + [key for key, _ in MEASUREMENT_FIELDS]
STYLE_HEADERS = ["order_id"] + list(STYLE_GROUPS.keys())


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def clean_num(value):
    """Parses a numeric input safely; returns 0.0 for blanks/garbage."""
    if value is None:
        return 0.0
    text = str(value).strip().replace(",", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


def next_id(records, prefix, start=101):
    """Auto-generates the next sequential id for a record set (e.g. C-102)."""
    nums = []
    for record in records:
        rid = str(record.get("id") or "")
        if rid.startswith(prefix + "-"):
            try:
                nums.append(int(rid.split("-", 1)[1]))
            except (ValueError, IndexError):
                continue
    return f"{prefix}-{max(nums) + 1 if nums else start}"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(form):
    """Returns a list of human-readable errors for an order-card submission."""
    errors = []
    name = str(form.get("name") or "").strip()
    phone = str(form.get("phone") or "").strip()
    date = str(form.get("date") or "").strip()

    if not name:
        errors.append("Customer name is required.")
    if not phone:
        errors.append("Mobile number is required.")
    else:
        digits = "".join(ch for ch in phone if ch.isdigit())
        if not digits:
            errors.append("Mobile number must contain digits.")
    if not date:
        errors.append("Date is required.")

    total = clean_num(form.get("total"))
    advance = clean_num(form.get("advance"))
    if advance > total:
        errors.append("Advance paid cannot exceed the total amount.")

    selected = [g for g in form.get("garments") or [] if str(g).strip()]
    if not selected:
        errors.append("Select at least one garment type.")

    return errors


def compute_remaining(total, advance):
    """Remaining balance = total - advance (never negative)."""
    return max(0.0, round(clean_num(total) - clean_num(advance), 2))


def gather_measurements(form):
    """Reads measurement values from the form into a clean float string map."""
    return {key: str(clean_num(form.get(key))) for key, _ in MEASUREMENT_FIELDS}


def gather_styles(form):
    """Reads the six style selections from the form."""
    return {key: str(form.get(key) or "").strip() for key in STYLE_GROUPS}


# ---------------------------------------------------------------------------
# Record builders
# ---------------------------------------------------------------------------

def customer_row(form, customer_id):
    """Builds a customers.xlsx row dict from the form."""
    meas = gather_measurements(form)
    # Map order-card measurement keys onto the legacy customer card columns.
    legacy = {
        "length": meas["lambai"],
        "sleeve": meas["sleeve"],
        "shoulder": meas["shoulder"],
        "collar": meas["collar"],
        "chest": meas["chest"],
        "waist": meas["waist"],
        "daman": meas["daman"],
        "shalwar_len": meas["shalwar_length"],
        "paancha": meas["paancha"],
    }
    return {
        "id": customer_id,
        "name": str(form.get("name") or "").strip(),
        "phone": str(form.get("phone") or "").strip(),
        **{key: value for key, value in legacy.items()},
        "address": str(form.get("address") or "").strip(),
        "created_date": str(form.get("date") or today_str()),
    }


def order_row(form, order_id, customer_id, customer_name):
    """Builds an orders.xlsx row dict from the form.
    Orders store a reference to a customer by ID (customer_id) instead of
    duplicating customer contact or measurement data. The customer_name is
    still accepted for convenience but not persisted into the order row.
    """
    total = clean_num(form.get("total"))
    advance = clean_num(form.get("advance"))
    garments = ", ".join(g for g in (form.get("garments") or []) if str(g).strip())
    styles = gather_styles(form)
    return {
        "id": order_id,
        "customer_id": customer_id,
        "garment": garments or "Kameez",
        "status": str(form.get("status") or "Pending"),
        "tailor": str(form.get("tailor") or "").strip(),
        "collar_style": styles["collar_style"],
        "cuff_style": styles["cuff_style"],
        "pocket_style": styles["pocket_style"],
        "daman_style": styles["daman_style"],
        "stitching": styles["stitching"],
        "button_style": styles["button_style"],
        "order_date": str(form.get("date") or today_str()),
        "delivery_date": str(form.get("delivery_date") or "").strip(),
        "delivery_time": str(form.get("delivery_time") or "").strip(),
        "delivered_by": str(form.get("delivered_by") or "").strip(),
        "delivery_status": str(form.get("delivery_status") or "Not Delivered"),
        "notes": str(form.get("notes") or "").strip(),
        "total": f"{total:.2f}",
        "advance": f"{advance:.2f}",
        "remaining": f"{compute_remaining(total, advance):.2f}",
    }


def measurement_row(order_id, form):
    return {"order_id": order_id, **gather_measurements(form)}


def style_row(order_id, form):
    return {"order_id": order_id, **gather_styles(form)}


# ---------------------------------------------------------------------------
# Persistence (shared by GUI and API)
# ---------------------------------------------------------------------------

def _customer_exists(customers, customer_id):
    return any(str(c.get("id") or "") == customer_id for c in customers)


def save_customer(excel_mgr, customers, form, customer_id):
    """Persists only the customer card (profile + legacy measurements)."""
    row = customer_row(form, customer_id)
    rows = [r for r in customers if str(r.get("id") or "") != customer_id]
    rows.append(row)
    excel_mgr.write_all_records("customers.xlsx", CUST_HEADERS,
                                [[r.get(h, "") for h in CUST_HEADERS] for r in rows])
    return row


def save_order(excel_mgr, customers, orders, form, customer_id=None, order_id=None):
    """Persists customer + order + measurements + styles. Returns saved ids.

    Existing customers/orders are updated in place; new ones are created with
    auto-generated ids.
    """
    errors = validate(form)
    if errors:
        raise ValueError("; ".join(errors))

    if not customer_id or not _customer_exists(customers, customer_id):
        customer_id = next_id(customers, "C", 101) if not customer_id else customer_id
    if not order_id:
        order_id = next_id(orders, "ORD", 101)

    cust_name = str(form.get("name") or "").strip()

    # Customer (upsert)
    cust_rows = [r for r in customers if str(r.get("id") or "") != customer_id]
    cust_rows.append(customer_row(form, customer_id))
    excel_mgr.write_all_records("customers.xlsx", CUST_HEADERS,
                                [[r.get(h, "") for h in CUST_HEADERS] for r in cust_rows])

    # Order (upsert)
    ord_rows = [r for r in orders if str(r.get("id") or "") != order_id]
    ord_rows.append(order_row(form, order_id, customer_id, cust_name))
    excel_mgr.write_all_records("orders.xlsx", ORD_HEADERS,
                                [[r.get(h, "") for h in ORD_HEADERS] for r in ord_rows])

    # Measurements + Styles (keyed by order_id)
    meas_rows = excel_mgr.read_records("measurements.xlsx", MEAS_HEADERS)
    meas_rows = [r for r in meas_rows if str(r.get("order_id") or "") != order_id]
    meas_rows.append(measurement_row(order_id, form))
    excel_mgr.write_all_records("measurements.xlsx", MEAS_HEADERS,
                                [[r.get(h, "") for h in MEAS_HEADERS] for r in meas_rows])

    style_rows = excel_mgr.read_records("styles.xlsx", STYLE_HEADERS)
    style_rows = [r for r in style_rows if str(r.get("order_id") or "") != order_id]
    style_rows.append(style_row(order_id, form))
    excel_mgr.write_all_records("styles.xlsx", STYLE_HEADERS,
                                [[r.get(h, "") for h in STYLE_HEADERS] for r in style_rows])

    return customer_id, order_id


def save_order_for_customer(excel_mgr, customers, orders, form, customer_id, order_id=None):
    """Save an order for an existing customer without changing that profile."""
    if not customer_id or not _customer_exists(customers, customer_id):
        raise ValueError("Select an existing customer before saving an order.")

    errors = validate(form)
    if errors:
        raise ValueError("\n".join(errors))

    customer = next(c for c in customers if str(c.get("id") or "") == customer_id)
    customer_name = str(customer.get("name") or form.get("name") or "").strip()
    if not order_id:
        order_id = next_id(orders, "ORD", 101)

    ord_rows = [r for r in orders if str(r.get("id") or "") != order_id]
    ord_rows.append(order_row(form, order_id, customer_id, customer_name))
    excel_mgr.write_all_records("orders.xlsx", ORD_HEADERS,
                                [[r.get(h, "") for h in ORD_HEADERS] for r in ord_rows])

    meas_rows = excel_mgr.read_records("measurements.xlsx", MEAS_HEADERS)
    meas_rows = [r for r in meas_rows if str(r.get("order_id") or "") != order_id]
    meas_rows.append(measurement_row(order_id, form))
    excel_mgr.write_all_records("measurements.xlsx", MEAS_HEADERS,
                                [[r.get(h, "") for h in MEAS_HEADERS] for r in meas_rows])

    style_rows = excel_mgr.read_records("styles.xlsx", STYLE_HEADERS)
    style_rows = [r for r in style_rows if str(r.get("order_id") or "") != order_id]
    style_rows.append(style_row(order_id, form))
    excel_mgr.write_all_records("styles.xlsx", STYLE_HEADERS,
                                [[r.get(h, "") for h in STYLE_HEADERS] for r in style_rows])
    return customer_id, order_id


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------

def build_receipt_text(form, customer_id, order_id):
    """Plain-text receipt suitable for any text/thermal printer."""
    total = clean_num(form.get("total"))
    advance = clean_num(form.get("advance"))
    remaining = compute_remaining(total, advance)
    garments = ", ".join(g for g in (form.get("garments") or []) if str(g).strip())
    styles = gather_styles(form)

    divider = "=" * 40
    thin = "-" * 40
    lines = [
        "JHAGRA CREATION & FABRICS".center(40),
        "The Name Of Quality - JTQ".center(40),
        divider,
        f"Order No : {order_id}",
        f"Customer : {str(form.get('name') or '').strip()}",
        f"Mobile   : {str(form.get('phone') or '').strip()}",
        f"Date     : {str(form.get('date') or today_str())}",
        thin,
        f"Garment(s) : {garments}",
        f"Status     : {str(form.get('status') or 'Pending')}",
        thin,
        f"Total     : PKR {total:.2f}",
        f"Advance   : PKR {advance:.2f}",
        f"Remaining : PKR {remaining:.2f}",
        divider,
        f"Collar : {styles['collar_style']}   Cuff : {styles['cuff_style']}",
        f"Pocket : {styles['pocket_style']}   Button : {styles['button_style']}",
        f"Daman : {styles['daman_style']}   Stitch : {styles['stitching']}",
        divider,
        "Thank you! Please bring receipt for pickup.".center(40),
    ]
    return "\n".join(lines)


def write_receipt_pdf(file_path, form, customer_id, order_id):
    """Writes an A5 PDF receipt mirroring the physical JTQ slip layout."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A5

    total = clean_num(form.get("total"))
    advance = clean_num(form.get("advance"))
    remaining = compute_remaining(total, advance)
    meas = gather_measurements(form)
    styles = gather_styles(form)

    c = canvas.Canvas(file_path, pagesize=A5)
    width, height = A5

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height - 50, "JHAGRA CREATION & FABRICS")
    c.setFont("Helvetica", 10)
    c.drawString(40, height - 65, "The Name Of Quality - JTQ")
    c.line(40, height - 75, width - 40, height - 75)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, height - 100, f"No: {order_id}")
    c.drawString(160, height - 100, f"Name: {str(form.get('name') or '').strip()}")
    c.drawString(40, height - 120, f"Contact: {str(form.get('phone') or '').strip()}")
    c.drawString(40, height - 140, f"Date: {str(form.get('date') or today_str())}")
    c.drawString(40, height - 160, f"Garments: {', '.join(str(g) for g in (form.get('garments') or []))}")

    # Measurements column (right side of the physical slip)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, height - 190, "Measurements (Inches)")
    c.setFont("Helvetica", 10)
    y = height - 210
    for key, label in MEASUREMENT_FIELDS:
        c.drawString(50, y, f"{label}:")
        c.drawString(170, y, str(meas.get(key, "0")))
        c.line(165, y - 2, 230, y - 2)
        y -= 18

    # Styles column (center of the physical slip)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(270, height - 190, "Selected Styles")
    c.setFont("Helvetica", 10)
    y = height - 210
    for key, (label, _) in STYLE_GROUPS.items():
        c.drawString(270, y, f"{label}: {styles.get(key) or 'None'}")
        y -= 18

    # Payment block
    c.setFont("Helvetica-Bold", 12)
    c.drawString(270, y - 10, "Payment")
    c.setFont("Helvetica", 10)
    c.drawString(270, y - 30, f"Total     : PKR {total:.2f}")
    c.drawString(270, y - 48, f"Advance   : PKR {advance:.2f}")
    c.drawString(270, y - 66, f"Remaining : PKR {remaining:.2f}")

    c.save()
