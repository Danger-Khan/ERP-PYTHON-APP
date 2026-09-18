# Change 6 — Full Urdu/English i18n wiring for Order Card + New Customer modal

**Date:** 2026-09-09

## Summary
Previously only the Order Card's title/subtitle actually translated on a
language switch; everything else (section headers, field labels, garment and
style chip text, buttons, dropdowns) and the entire New Customer modal stayed
in English regardless of the selected language. Wired up full translation
for both screens:

- **`app/views/order_card_view.py`** (substantial rewrite): all 6 section
  headers, every field label, all garment chips, all style-group labels and
  their option chips across all 8 groups, and the 3 action buttons now
  re-render via `set_language()`.
  - `ChipGroup`/`ChipCheckGroup` were refactored to separate a chip's
    canonical stored *value* from its displayed *label*, with a new
    `relabel()` method that updates on-screen text without touching the
    selection or the underlying value.
  - New `TranslatedCombobox` wrapper does the same for the Order
    Status / Delivery Status dropdowns.
  - This decoupling matters because `main_gui.py` elsewhere compares status
    strings literally in English (dashboard charts, row coloring, the "Mark
    Ready" quick-action) — translating the *displayed* text without this
    separation would have caused orders saved while in Urdu mode to store
    Urdu status/garment/style text and silently vanish from those
    English-keyed comparisons.
- **`app/main_gui.py`**, `open_add_customer_modal`: now builds using
  `TRANSLATIONS[self.current_lang]` (merged with English fallback) so it
  opens in whichever language is currently active — title, heading,
  Name/Phone/Address labels, all 9 measurement labels (replacing the old
  hardcoded mixed English/Urdu-script hint text), and the Save button.
- **`app/lang/en.py`**: added the English versions of every new key
  (mandatory — the app's language-merge logic does direct `dict[key]`
  lookups, so a key missing from `en.py` would `KeyError` even in English
  mode).
- **`app/lang/ur.py`**: added the remaining `oc_*` (order-card chrome) and
  `nc_*` (new-customer modal) keys not already added in change 0.

## Why
User: "i need this all change to urdu as well when i cange from en to ur,"
referencing screenshots showing the Order Card and New Customer modal
mostly still in English after a language switch.

## Files touched
- `app/views/order_card_view.py`
- `app/main_gui.py`
- `app/lang/en.py`
- `app/lang/ur.py`

## Verification
- Full pytest suite: 12/12 passed.
- GUI smoke test: 23/23 passed.
- A 28-check targeted script covering: EN baseline text/values, switching to
  UR via the real UI control path, every section header/field
  label/chip/button/dropdown showing translated text, selection state
  surviving the relabel, canonical English values still returned by
  `.selected()`/`.get()` while UI is in Urdu, the New Customer modal opening
  in Urdu, a full order save performed while in Urdu mode confirmed to land
  in `orders.xlsx` still in English (garment/status/style columns), and
  switching back to English restoring everything cleanly.

## Explicitly out of scope (flagged, not done)
Validation error messages and the printed/PDF receipt text
(`order_card_service.py`) are not translated — that module is shared
between the desktop GUI and the Flask API, so wiring translation into it
needs more care than the screenshots called for. `ur.py` already has the
Urdu strings ready (`err_*`, `receipt_*`) if this is wanted next. Pashto,
Chinese, and Russian language packs were not updated for the new keys —
they safely fall back to English, consistent with the app's existing
partial-language-pack design.
