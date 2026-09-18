# Change 2 — Order card: removed per-order Measurements section (v1)

**Date:** 2026-09-09

## Summary
Removed the "3 · Measurements" input section from the Order Card screen
(`app/views/order_card_view.py`). In its place, added a read-only "Saved
Measurements" block in the Customer Information section that auto-fills from
the selected customer's own record once a customer is chosen.

(Note: this display block was itself removed later — see change 5 — once the
user pointed out it duplicated what's already visible on the Customer card.)

## Why
User asked to remove measurements from the order card and use the value
already saved in the customer section instead of re-entering it per order.

## Files touched
- `app/views/order_card_view.py`

## Verification
- Full pytest suite: 12/12 passed.
- GUI smoke test: 23/23 passed (including dark theme, both Add modals).
