# Change 4 — UI visual-consistency / dark-mode polish pass

**Date:** 2026-09-09

## Summary
Ran a background audit of `app/main_gui.py` for visual-consistency and
dark-mode-safety issues (explicitly excluding `order_card_view.py`, per
user's instruction not to touch that screen's patterns). Fixed the
highest-impact findings, all cosmetic only:

1. Every `tk.Entry` field (login password, customer search, garment/role
   inputs, all Add/Edit modal fields) now themes correctly — previously
   stayed white-on-black regardless of theme.
2. `ttk.Combobox` fields and their dropdown lists now theme correctly
   (status/theme/language/role/staff pickers).
3. Dashboard donut-chart "track" ring now uses the theme border color
   instead of a hardcoded light gray.
4. Edit Customer / Edit Staff dialogs now match the Add dialogs' button
   style (full-width, `cursor="hand2"`, bold font) and label font.
5. Search "Clear" button now has a visible border instead of blending into
   the background in dark mode.
6. Minor sizing consistency: dashboard "Mark Ready" button and the Customer
   Hub search label now match their equivalents elsewhere.

## Why
User asked for a UI polish/consistency pass on the app (excluding the order
card and new customer card's fields/patterns/values, cosmetic changes only
there).

## Files touched
- `app/main_gui.py`

## Verification
- Full pytest suite: 12/12 passed.
- GUI smoke test: 23/23 passed, including explicit dark-theme and both
  Add-modal checks.

## Deferred (lower priority, flagged not done)
Card padding standardization (dashboard vs. settings cards), a formal
button-size tier system, per-column Treeview widths, and confirming/removing
`open_add_order_modal` (looks like dead code superseded by the Order Card
screen).
