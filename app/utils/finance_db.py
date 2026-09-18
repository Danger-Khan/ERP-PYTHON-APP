"""SQLite-backed finance ledger for the Tkinter ERP app.

Orders themselves stay in orders.xlsx (ExcelManager remains the source of
truth for order/customer data everywhere else in the app). This module's
only job is to hold the *numbers that matter for finance* — paid,
remaining, and debt per order, plus shop-wide totals — in a real SQL
table, computed fresh from the live order records on every sync() call and
queried back out with actual SQL rather than re-derived ad hoc in the GUI.

Definitions (confirmed with the shop owner):
- paid       = the order's advance/amount already collected.
- remaining  = unpaid balance on an order that has NOT been delivered yet
               (normal, expected — work still in progress).
- debt       = unpaid balance on an order that HAS been delivered/handed
               over (or partially handed over) — the customer already has
               the goods but still owes money, i.e. real receivable risk.
A given order's balance is either counted as "remaining" or as "debt",
never both, so paid + remaining + debt across all orders reconciles to
the shop's total order value.
"""
import os
import sqlite3
from datetime import datetime

DELIVERED_STATES = ("delivered", "partial")


def _num(v):
    """Best-effort float coercion; blank/garbage -> 0.0."""
    try:
        return round(float(str(v).strip() or 0), 2)
    except (TypeError, ValueError):
        return 0.0


class FinanceDB:
    """Thin wrapper around a small `order_finance` SQLite table."""

    def __init__(self, data_dir):
        os.makedirs(data_dir, exist_ok=True)
        self.db_path = os.path.join(data_dir, "finance.db")
        self._init_schema()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS order_finance (
                    order_id        TEXT PRIMARY KEY,
                    customer_id     TEXT,
                    customer_name   TEXT,
                    garment         TEXT,
                    status          TEXT,
                    delivery_status TEXT,
                    total           REAL NOT NULL DEFAULT 0,
                    paid            REAL NOT NULL DEFAULT 0,
                    remaining       REAL NOT NULL DEFAULT 0,
                    debt            REAL NOT NULL DEFAULT 0,
                    updated_at      TEXT
                )
            """)
            conn.commit()

    def sync(self, orders, customers):
        """Recompute every order's paid/remaining/debt from the live order
        records passed in (already read from orders.xlsx) and replace the
        table contents in one transaction. Cheap enough to call after every
        data reload — the table only ever holds one row per order."""
        cust_names = {str(c.get("id") or "").strip(): str(c.get("name") or "").strip() for c in customers}
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows = []
        for o in orders:
            order_id = str(o.get("id") or "").strip()
            if not order_id:
                continue
            total = _num(o.get("total"))
            paid = _num(o.get("advance"))
            remaining_calc = max(0.0, round(total - paid, 2))
            # Trust the stored "remaining" field when present (it's the same
            # number order_card_service.compute_remaining() wrote), fall
            # back to recomputing it so old rows without the field still work.
            stored_remaining = _num(o.get("remaining"))
            balance = stored_remaining if o.get("remaining") not in (None, "") else remaining_calc

            status = str(o.get("status") or "").strip()
            delivery_status = str(o.get("delivery_status") or "").strip()
            delivered = status.lower() == "delivered" or delivery_status.lower() in DELIVERED_STATES

            debt = balance if delivered else 0.0
            remaining = 0.0 if delivered else balance
            customer_id = str(o.get("customer_id") or "").strip()

            rows.append((
                order_id, customer_id, cust_names.get(customer_id, ""),
                str(o.get("garment") or "").strip(), status, delivery_status,
                total, paid, remaining, debt, now
            ))

        with self._connect() as conn:
            conn.execute("DELETE FROM order_finance")
            conn.executemany(
                """INSERT INTO order_finance
                   (order_id, customer_id, customer_name, garment, status, delivery_status,
                    total, paid, remaining, debt, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                rows,
            )
            conn.commit()

    def get_totals(self):
        """Shop-wide SUM(...) aggregates via SQL — used by the Dashboard's
        finance card and the Finance view's summary strip."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(paid),0), COALESCE(SUM(remaining),0), COALESCE(SUM(debt),0) "
                "FROM order_finance"
            ).fetchone()
        return {"paid": round(row[0], 2), "remaining": round(row[1], 2), "debt": round(row[2], 2)}

    def get_rows(self):
        """Per-order breakdown, orders with an open balance surfaced first."""
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM order_finance "
                "ORDER BY (debt > 0) DESC, (remaining > 0) DESC, order_id"
            )
            return [dict(r) for r in cur.fetchall()]
