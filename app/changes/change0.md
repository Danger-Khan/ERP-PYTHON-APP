# Change 0 — Urdu translations for order-card terms

**Date:** 2026-09-09

## Summary
Added ~90 Urdu translation entries to `app/lang/ur.py` for every English string
used in `app/services/order_card_service.py`: the 7 garment options, all 15
measurement field labels, all 8 style groups and their option choices, order
and delivery statuses, the 7 validation error messages, and the printed/PDF
receipt text labels.

## Why
The order card (and its underlying service module) only existed in English.
The user asked for Urdu translations for every term used there, as groundwork
for the app displaying in Urdu.

## Files touched
- `app/lang/ur.py` — added `garment_*`, `meas_*`, `style_*`, `status_*`,
  `err_*`, `receipt_*` keys to `TRANSLATIONS`.

## Verification
Visual review of the added dict (balanced braces, consistent
`"key": "value"` entries). Not yet wired into any UI at this point — that
wiring came later (see change 6). No automated test covers this file
directly.

## Note
This was translation-data-only; nothing in the app read these keys yet.
