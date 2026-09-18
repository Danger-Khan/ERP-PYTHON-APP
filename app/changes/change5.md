# Change 5 — Order card: fully removed measurement display; New Customer modal: added Address

**Date:** 2026-09-09

## Summary
Two related fixes:

1. **Order Card** (`app/views/order_card_view.py`): removed the "Saved
   Measurements" read-only display block added in change 2 — it duplicated
   what's already shown on the Customer card, so the user asked for it to
   be dropped from the order card entirely. The underlying behavior is
   unchanged: saving an order still snapshots the selected customer's
   current measurements into `measurements.xlsx` via a new
   `_customer_measurements()` helper that looks the values up directly from
   `self.app.customers`, it just isn't shown on screen anymore.
2. **New Customer modal** (`app/main_gui.py`,
   `open_add_customer_modal`): found and fixed a real gap — the customer
   schema (`cust_headers`) has always included `address` and `created_date`
   columns, but the modal never collected them, so every customer created
   through it silently got a blank address forever. Added an **Address**
   field to the form, and `created_date` now auto-fills to today's date
   (matching how dates are auto-set elsewhere in the app).

## Why
User: "remove the length and sizes from order card it is already there in
new customer card and in new customer card do must add the address and
other details."

## Files touched
- `app/views/order_card_view.py`
- `app/main_gui.py`

## Verification
- Full pytest suite: 12/12 passed.
- GUI smoke test: 23/23 passed.
- Targeted script confirming: no `cust_meas_entries` widgets remain on
  `OrderCardView`; customer info (incl. address) still auto-fills on
  selection; `collect_form()` still supplies all 9 mapped measurements
  sourced from the customer record; a full order save still writes a
  correct measurement snapshot to `measurements.xlsx`.
- Separate targeted script confirming the New Customer modal now saves
  `address` and `created_date` correctly to `customers.xlsx`.
