# Change 14 — Reverted retheme colors, added donut circles to Dashboard finance cards

**Date:** 2026-09-18

## Summary
- **Reverted the monochrome retheme from change13**: user clarified the
  reference-design ask was about column/block *layout*, not color — "the
  original coloring was good." Restored `PRIMARY` to blue (`#007AFF`), the
  original soft-glass `THEMES` palette (light + dark), and the
  light-catching `glass_highlight` top strip on cards in both
  `main_gui.py`'s `_glass_card()` and `order_card_view.py`'s `_card()`
  (both had been flattened). `ACCENT_BLUE`/`ACCENT_RED` for the tri-color
  header strip stay hardcoded independently of `PRIMARY`/`DANGER` as
  before — harmless now that they match again, but keeps the strip safe
  from future palette retuning either way. README color tables reverted
  to match. Analyzed the reference screenshots for their actual
  column/block layout patterns (two-column page splits, compound table
  cells, status pills, paired footer utility cards, sidebar profile block,
  segmented card-header tabs, pagination) and reported them back rather
  than guessing which to build next.
- **Added donut circles to the Dashboard's finance snapshot cards**,
  matching the existing Work Done / In Progress / Remaining donuts: each
  of Total Paid / Total Remaining / Total Debt now has a
  `CircularDonutChart` showing that bucket's share of the shop's total
  order value (`paid + remaining + debt`), colored the same as its label
  (green/orange/red). Computed and set in `refresh_finance_ui()` alongside
  the existing PKR labels — no new refresh path.

## Why
Two follow-on corrections/requests: "i mean by the column and blocks not
their coloring the original coloring was good" (color revert), and "the
circles for finance as there for order in dashboard card add them" (donut
parity between the order and finance stat rows).

## Files touched
- `app/main_gui.py` (`THEMES`, `PRIMARY`, `_glass_card`, Dashboard finance
  card donuts, `refresh_finance_ui` percentage calc)
- `app/views/order_card_view.py` (`_card()` highlight strip restored)
- `app/README.md`, `app/readme.txt`, `app/readme.me` (color table revert)

## Verification
- pytest: 12/12. GUI smoke test: 39/39 (unaffected — palette/donut
  additions don't touch any check, and the theme checks already compare
  against `gui.THEMES[...]` directly).
- Screenshotted the real running Dashboard: confirmed the blue nav/accent
  colors are back, and the three finance cards now show partial donut
  rings (Paid ~33% green, Remaining ~67% orange, Debt 0% on the seeded
  data) exactly like the order status row above them.
