# Change 10 — Icons added across the UI (chrome only, no field/value changes)

**Date:** 2026-09-10

## Summary
Added emoji icons wherever they fit naturally, matching the style already
used by buttons like `➕ Add Customer` / `🖨️ New Order Card`:

- **Sidebar nav** (all 6 items, incl. the new Finance tab): 📊 Dashboard,
  👥 Customers, 📝 Order Card, 👷 Employees, 💰 Finance, ⚙️ Settings.
- **Dashboard stat cards**: ✅ Work Done, ⏳ In Progress, ⏰ Remaining, plus
  the finance snapshot row: 💵 Total Paid, ⏳ Total Remaining, ⚠️ Total Debt.
- **Finance view** summary cards get the same 💵/⏳/⚠️ treatment.
- **Action buttons** that previously had no icon: Edit (✏️), Delete (🗑️),
  Print Latest Receipt / Print Task Slip (🧾), Save Staff / Save Changes /
  Save Customer / Save Order (💾), Clear Form / Clear search (🧹 / ✖),
  Assign Task submit (✅), Place Order (✅), Login to Dashboard (🔐).
- **Order Card section headers** (chrome only — "1 · Customer Information"
  etc.): 👤 Customer Information, 👕 Garment Type, 🎨 Style Options,
  📝 Special Notes, 🚚 Delivery, 💳 Payment.
- **New Customer modal**: 📋 Register Measurements (window title),
  📏 Customer Profile & Measurements (heading), 💾 Save Customer.
- **Add/Edit Staff and Assign Task modal** titles/headings/buttons.
- Every icon added to a lang-driven string went into **both**
  `app/lang/en.py` and `app/lang/ur.py`, so it survives switching to Urdu
  (icons themselves don't need translating — same emoji, translated text).

**Deliberately left untouched** (per the standing "don't change order
card / new customer card patterns, blanks or values" instruction): the
actual field labels (Name, Mobile Number, Date, etc.), the garment/style
selection chips (Kameez, Shalwar, Baz Button, Normal, ...), and status
values. Icons only went on section headers and action buttons — chrome,
not the form itself. Table column headers were also left plain (no
existing precedent for per-column icons in this app).

## Why
User: "add icons where possible" — a follow-on visual-polish pass after
the soft-glass styling (change8) and the new Finance view (change9).

## Files touched
- `app/lang/en.py`, `app/lang/ur.py` (icon prefixes on ~35 nav/button/
  header/card-title keys)
- `app/main_gui.py` (icon prefixes on the handful of hardcoded button
  strings not sourced from the lang dict: login button, customer
  Edit/Delete/Print Latest Receipt, search Clear, Place Order, the
  customer-edit dialog's Save Changes)
- `app/tests/gui_smoke_test.py` ("english nav restored" now checks
  `"Dashboard" in text` instead of exact equality, since the nav label is
  now `"📊 Dashboard"`)

## Verification
- pytest: 12/12. GUI smoke test: 29/29.
- Launched the real app on-screen and screenshotted Dashboard, Customers,
  Employees, Finance, Order Card, and the New Customer modal: confirmed
  every icon renders correctly (Windows' Segoe UI Symbol/Emoji fallback
  draws them cleanly), buttons stay readable at their existing size, and
  no order-card or new-customer field/value/pattern changed — only
  section headers and action-button chrome gained icons.
