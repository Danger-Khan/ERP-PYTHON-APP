# Change 9 — Finance view + Dashboard finance card (SQLite-backed)

**Date:** 2026-09-10

## Summary
- New `app/utils/finance_db.py` (`FinanceDB`): a small SQLite database
  (`finance.db`, colocated with whichever data dir `ExcelManager` currently
  points to) holding one `order_finance` row per order — `total`, `paid`,
  `remaining`, `debt`. Orders/customers stay in Excel as the source of
  truth; this table is fully recomputed from live order records on every
  `sync()` call (cheap — one `DELETE` + `executemany` per reload), so it's
  always a mirror, never a second source of truth to keep in sync by hand.
  Totals and per-order rows are read back out with real SQL
  (`SUM(...)`, `ORDER BY`), not recomputed ad hoc in Tkinter code.
- **Definitions** (confirmed with the user before building): `paid` = an
  order's advance/amount collected. `remaining` = unpaid balance on an
  order **not yet delivered** (normal, expected). `debt` = unpaid balance
  on an order that **has been delivered/handed over** (or partially) — the
  customer already has the goods but still owes money, i.e. real
  receivable risk, tracked separately from ordinary WIP `remaining`.
- `main_gui.py`: `reload_all_data()` now calls
  `FinanceDB.sync(self.orders, self.customers)` at the end of every data
  load (login, the 5s auto-refresh loop, every order/customer/employee
  write) — non-fatal on failure so a locked `finance.db` never blocks the
  rest of the app.
- New **Finance** section (new sidebar nav entry, between Employees and
  Settings): 3 glass summary cards (Total Paid / Total Remaining / Total
  Debt) + a per-order ledger table (order, customer, garment, total, paid,
  remaining, debt, status, delivery status), red/orange row-tinted by
  whether that order carries debt or just remaining balance.
- **Dashboard**: new finance snapshot row (3 glass cards, same numbers) added
  directly under the existing WORK DONE / IN PROGRESS / REMAINING row, so
  the money picture is visible without leaving the Dashboard.
- Both the Finance section and Dashboard finance cards are refreshed by one
  shared `refresh_finance_ui()`, called from the existing
  `update_graphics_and_stats()` — no new refresh loop, reuses the app's
  existing "data changed -> repaint" path.
- Full i18n: new `nav_finance`, `dash_fin_*`, `fin_*` keys added to both
  `app/lang/en.py` and `app/lang/ur.py` (nav label, section title/subtitle,
  card titles, table headers) and wired into `apply_language_pack()`.
- New cards use the existing `_glass_card()` helper, so they match the
  soft-glass styling from change8 in both light and dark theme automatically.

## Why
User: "in the apk i need the finance view card. that will need to track the
finance of customer order, the one paid, the one remaining and the one
debt. also need its update on main dashboard card. do manage the
background of the finance and numerical values related to finance in sql
format." Clarified with the user first: debt = delivered-but-unpaid vs.
remaining = still-in-progress-and-unpaid (not the same number shown
twice), and "SQL format" = a real local SQLite database for the finance
figures specifically (not just formatting numbers), while Excel stays the
source of truth for orders/customers everywhere else in the app.

## Files touched
- `app/utils/finance_db.py` (new)
- `app/main_gui.py` (import, `_finance_db_for_current_data`, finance sync
  hook in `reload_all_data`, Dashboard finance row, new
  `build_finance_section`/`refresh_finance_ui`, nav entry, language wiring)
- `app/lang/en.py`, `app/lang/ur.py` (new finance keys)
- `app/tests/gui_smoke_test.py` (second seeded order — Delivered with an
  unpaid balance — plus new checks for the Finance section and its totals)

## Verification
- pytest: 12/12. GUI smoke test: 29/29 (6 new checks: finance section nav,
  finance section visible, total paid/debt/remaining computed correctly
  from two seeded orders — one active+partially paid, one delivered+unpaid
  — and the ledger table row count).
- Actually launched the real app on-screen and screenshotted Dashboard and
  Finance in light mode, dark mode, and Urdu: confirmed the numbers match
  the seeded data (PKR 3,000 paid / 2,000 remaining / 3,000 debt), the
  delivered order's balance lands in the Debt column (not Remaining), the
  Urdu labels and RTL order-ID/customer table render correctly, and both
  themes stay legible.
