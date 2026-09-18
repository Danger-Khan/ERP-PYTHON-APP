# Change 13 — Remaining button translations wired, monochrome retheme

**Date:** 2026-09-18

## Summary

### 1. Closed remaining translation gaps
User asked for Add/Delete/Remove translations "by their each individual
card" for Staff, Employee, Customer, and the Dashboard/Finance/Settings
cards. Dashboard/Finance/Settings titles and Employee's Edit/Delete/Print
were already wired (change9/change10); the real gaps closed here:
- **Customer section**: Edit, Delete, and Print Latest Receipt buttons
  were hardcoded English regardless of language — now driven by new
  `cust_btn_edit`/`cust_btn_delete`/`cust_btn_receipt` keys, wired at both
  construction time and in `apply_language_pack()`.
- **Settings**: the Garment Types / Employee Roles card titles and their
  Add/Remove buttons were hardcoded too — now `admin_card_garments`,
  `admin_card_roles`, and shared `btn_item_add`/`btn_item_remove` keys
  (four button widgets captured as `self.btn_add_garment`/
  `btn_remove_garment`/`btn_add_role`/`btn_remove_role` so language switch
  can reach them).
- Bigger find while auditing: `btn_add_cust`, `btn_new_card`,
  `btn_assign_task`, `btn_add_emp`, and the Dashboard ledger's table
  headers (`tbl_ord_id`/`tbl_cust`/`tbl_garment`/`tbl_status`/`tbl_tailor`)
  didn't exist in `ur.py` at all — switching to Urdu silently left these
  showing English (the merge-fallback logic masks a missing key instead of
  erroring). Added all of them to `ur.py`.

### 2. Monochrome retheme (from a reference design)
User shared several screenshots of a flat black/white/gray SaaS-style
reference ("Farman Clothes") and asked the app look closer to it, keeping
all content — especially the Order Card — unchanged. Implemented as a
palette/chrome retune, not a content rebuild:
- **`PRIMARY` changed from blue (`#007AFF`) to near-black (`#111214`)**.
  Because `PRIMARY` already drives the nav active pill, primary buttons,
  Treeview/Combobox selection color, and (passed through as a constructor
  arg) the Order Card's selected style chips, this single constant change
  cascades correctly everywhere without touching call sites — nav active
  state and primary CTAs now read as black-on-white, matching the
  reference.
- **`THEMES` light palette retuned** to a flatter, cooler white/gray:
  `bg_body #F7F8FA`, `bg_card #FFFFFF` (pure white, was an off-white
  blue-tinted `#FAFBFF`), `border #E5E7EB`, `text_main #111214`,
  `text_muted #6B7280`, `bg_chart #F3F4F6`. Dark theme similarly moved off
  its navy tint toward true near-black/gray (`bg_body #121212`,
  `bg_card #1E1E21`, `border #333333`).
- **`_glass_card()` (main_gui.py) and `_card()` (order_card_view.py)
  flattened**: removed the 2px "glass_highlight" top strip both drew,
  leaving a plain soft-bordered flat card — closer to the reference's flat
  cards than the previous frosted-glass look. Both keep their exact same
  shell+inner-frame signature, so every existing caller (dashboard tiles,
  settings cards, Finance cards, all 6 order-card sections) needed zero
  changes.
- **`ACCENT_BLUE`/`ACCENT_RED` decoupled from `PRIMARY`/`DANGER`**: the
  tri-color accent strip added earlier this session was tied to those two
  constants; now hardcoded to their original blue/red values directly, so
  it stays a genuine blue/white/red strip regardless of how the main
  palette gets retuned going forward.
- **Order Card deliberately untouched in every other respect**: same
  fields, same labels, same garment/style options, same values, same
  validation — only the shell color/border it sits in changed, per the
  standing "don't change order card patterns/blanks/values" instruction.

### 3. README color tables updated
`app/README.md`, `app/readme.txt`, and `app/readme.me` all updated to
describe "flat monochrome" instead of "soft-glassmorphism" and to list the
new hex values, with a note that the accent strip is intentionally
independent of the retuned Primary/Danger tokens.

## Why
Two follow-on requests in the same sitting as change11/12: (1) "make
translations for the options of like delete add remove staff, employee,
customer, dashboard, finance, settings by their each individual cards" —
closing the specific gaps found; (2) a shared reference-design screenshot
with "make it somehow closely to this gui while keeping the content as it
is specially order card" — a palette/chrome retune rather than a layout
rebuild, since the reference's actual information architecture (client
photo upload, referral source, garment "architecture" picker cards, etc.)
differs from this app's own screens and the user explicitly said to keep
content as-is.

## Files touched
- `app/main_gui.py` (button/label wiring for the translation gaps;
  `PRIMARY`, `THEMES`, `ACCENT_BLUE`/`ACCENT_RED`, `_glass_card`)
- `app/views/order_card_view.py` (`_card()` flattened)
- `app/lang/en.py`, `app/lang/ur.py` (new + backfilled keys)
- `app/README.md`, `app/readme.txt`, `app/readme.me` (palette description)

## Verification
- pytest: 12/12. GUI smoke test: 39/39 (unchanged — palette/wording
  changes don't touch the checks, and `gui_smoke_test.py`'s theme
  assertions already compare against `gui.THEMES[...]` directly rather
  than hardcoded hex, so a palette retune never staled them).
- Launched the real app on-screen and screenshotted Dashboard, Order Card,
  Settings, and Employee in both Light and Dark: confirmed the black
  active-nav pill, flat white cards, and black primary buttons read
  cleanly against the reference direction, the tri-color strip still
  shows true blue/white/red, and the Order Card's fields/values/layout
  are pixel-identical to before except for the new flat card color.
