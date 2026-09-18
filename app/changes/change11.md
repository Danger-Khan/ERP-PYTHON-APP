# Change 11 — Session persistence, Finance tabs + Add Payment, tri-color accent (part 1 of 2, continued in change12.md)

**Date:** 2026-09-18

## Summary

### 1. Settings/session persistence ("memory/cache file")
New `app/utils/app_state.py` (`AppStateCache`): a small JSON cache file at
`<data_dir>/cache/app_state_cache.json` holding theme, language, the last
open sidebar section, and window geometry. Loaded once at startup (before
the login screen is even shown, so the very first frame already reflects
last session's theme/language) and written back on every change that
matters: theme switch, language switch, section navigation, and on window
close (`WM_DELETE_WINDOW` now runs `on_app_close()`, which saves once more
before destroying, catching anything the per-action saves might have
missed). Closing and reopening the app now reliably lands back on the same
theme, language, section, and window size/position instead of always
resetting to English/Light/Dashboard/default size.

As a side effect of fixing this properly (see the bug note below), a
pre-existing rough edge got fixed too: switching theme used to always snap
the view back to Dashboard, because `build_ui_layout()` hardcoded
`show_section("dashboard")`. It now reopens on `self.current_section`
(tracked by `show_section()` itself), so a theme toggle keeps you exactly
where you were, and that's also the value written to the session cache.

### 2. Finance: Done / Due / Add Payment tabs
The Finance view now has a small tab bar above the ledger table: **All**,
**✅ Done**, **⚠️ Due**, and **➕ Add Payment**.
- **Done** filters to orders that are fully settled (`remaining <= 0`,
  `debt <= 0`, and `total > 0` — the total>0 guard excludes blank/legacy
  rows with no financial data at all from counting as "done").
- **Due** filters to orders carrying any outstanding balance (`remaining >
  0` or `debt > 0`), whether that balance is ordinary work-in-progress
  remaining or delivered-and-unpaid debt.
- **Add Payment** swaps the ledger table out for a small form: a dropdown
  of only the orders that currently have a due balance (labelled with the
  order, customer, and amount due), a payment-amount field, and a
  **💾 Record Payment** button.

New `main_gui.py` methods: `set_finance_tab(tab_key)` (switches which
container is shown and restyles the active tab button),
`_refresh_finance_payment_picker()` (rebuilds the due-orders dropdown from
`FinanceDB.get_rows()`), and `record_finance_payment()` — this increases
the selected order's `advance` field by the entered amount (capped at the
order's `total` so it can never go negative-remaining), recomputes
`remaining` via the existing `order_card_service.compute_remaining()`
helper, and writes the order back to `orders.xlsx` using the same
schema-aware full-row rewrite pattern already used by
`quick_change_order_status()` and `_assign_order_tailor()` (rebuild every
column from `ord_headers`, mutate only the two financial fields). After
saving it reloads all data (which re-syncs `finance.db`) and refreshes the
UI, so the Dashboard finance card, the Finance totals, and the ledger all
update immediately. `refresh_finance_ui()` now also takes the active tab
into account when populating `tree_finance`, instead of always showing
every order.

All four tab labels and the Add Payment form's labels are fully wired
through the existing `en.py`/`ur.py` translation dictionaries and
`apply_language_pack()`, matching the depth of i18n already done for the
rest of the app this session.

### 3. UI appeal and flexibility
- New thin **blue / white / red accent strip** (`_create_accent_strip()`)
  along the very top edge of the window, above the header bar — a small
  brand-color signature drawn from three equal segments, rebuilt on every
  theme switch alongside the rest of the layout. Purely decorative; it
  doesn't touch the header, sidebar, or any content.
- **Sidebar nav hover feedback**: nav buttons now lightly tint
  (`bg_chart`) on mouse-over when they aren't the already-active section,
  and revert on mouse-out — a small "the UI feels alive" touch that costs
  nothing structurally (bound via `<Enter>`/`<Leave>`, no layout change).
- **`self.minsize(1100, 700)`** so the window can be resized more freely
  without its own content starting to clip, and the saved geometry from
  the session cache is applied before the window is ever shown, so a user
  who prefers a bigger or smaller window keeps it every time.

### 4. Bug found and fixed while building the above
While wiring the settings cache, testing surfaced a real bug: `main_gui.py`
originally created `self.app_state = AppStateCache(self.excel_mgr.data_dir)`
**once**, eagerly, in `__init__` — before the GUI test suite (or anything
else) gets a chance to point `self.excel_mgr` at a different data
directory. Every later `.save()` call kept writing to that first-bound
path regardless of what `excel_mgr` later became, which meant the
permanent GUI smoke test was — silently — writing a real
`app/data/cache/app_state_cache.json` file into the actual production data
folder on every run, exactly the class of mistake flagged as a lesson in
an earlier session (change3.md: sandbox test writes more carefully). It
never touched customer/order/employee data and the written values were
always harmless defaults, but it was still the app leaking test state into
real storage.

Fixed by giving `app_state` the same lazy-rebind pattern `finance_db`
already used: a new `_app_state_for_current_data()` method that
(re)creates the `AppStateCache` against whichever directory
`self.excel_mgr.data_dir` currently points to, and every `.save()`/`.load()`
call site now goes through that accessor instead of touching
`self.app_state` directly. A second, smaller issue in the same vein was
also fixed: `AppStateCache.__init__` used to call `os.makedirs()`
immediately on construction (even for a read-only `.load()` that finds
nothing), which alone was enough to leave a stray `cache/` folder behind
in the real data dir the instant the app started — now only `save()`
creates the directory, so a session that never changes a setting never
touches the filesystem at all. The stray file this created during today's
own testing was deleted, and a fresh smoke test run was confirmed to leave
`app/data/` completely untouched afterward.

*(continued in [change12.md](change12.md): Documentation, Why, Files
touched, Verification)*
