# Change 8 — Soft-glass UI styling (whole app)

**Date:** 2026-09-09

## Summary
- Retuned `THEMES` (light + dark) in `main_gui.py` to a soft frosted-tint palette: cooler/softer `bg_body`, `bg_header`, `bg_sidebar`, `bg_card`, `bg_chart`, and lower-contrast `border` colors. Added a new `glass_highlight` token per theme for a thin light-catching strip. `text_main`/`text_muted` and the semantic accent colors (PRIMARY/SUCCESS/WARNING/DANGER) were left untouched — legibility and status-color meaning never traded away for looks.
- New `AtelierERPApp._glass_card()` helper: wraps a frosted shell (soft bg + soft border + 2px top highlight strip) around an inner content frame. Returns the inner frame so every caller keeps adding children exactly as before — zero layout/behavior changes. Applied to the 3 dashboard stat tiles, all 4 Settings cards, and the Assign Task modal's order-details box.
- Applied the same treatment to `order_card_view.py`'s centralized `_card()` helper (used by all 6 order-card sections).
- **Bug found + fixed while visually reviewing dark mode**: several `tk.Entry` fields in the order card (Date, Assign Tailor, Total, Advance) had a hardcoded/missing background, making dark-theme text nearly invisible against a stray white field. Also added `readonlybackground` to the read-only fields (Customer ID/Name/Mobile/Address), which Tkinter needs separately from `bg` for `state="readonly"` Entries — fixes an inconsistent gray look in light mode too.
- Fixed `gui_smoke_test.py`'s theme-check assertions, which hardcoded the old hex values; now compare against `gui.THEMES[...]` directly so future palette tweaks won't stale them out.

## Why
User: "do gui improvement i want soft glass morph texture without disturbing any content." Tkinter has no real background blur/transparency, so this is an approximated glass look via color/border choices only, confirmed with the user first (whole-app scope, faux-glass approach) since a literal blur hack would require restructuring cards onto Canvas.

## Files touched
- `app/main_gui.py` (THEMES, new `_glass_card`, 8 call sites)
- `app/views/order_card_view.py` (`_card`, `_row_entry`, `ent_total`/`ent_advance`)
- `app/tests/gui_smoke_test.py` (2 stale assertions)

## Verification
- pytest: 12/12. GUI smoke test: 23/23.
- Actually launched the real app on-screen (not headless) and captured real screenshots via PIL.ImageGrab (DPI-scale-corrected for this machine's 1.25x scaling) — Dashboard, Order Card, and Settings, in both light and dark mode. Visually confirmed the soft-glass cards render correctly and caught the Entry dark-mode bug this way before calling it done.
