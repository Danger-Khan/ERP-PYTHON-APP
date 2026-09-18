# Change 7 — Employee section i18n + Assign Task now links real orders

**Date:** 2026-09-09

## Summary
- **Employee section translation** (matching the Order Card/New Customer depth): Print/Edit/Delete buttons, all 6 employee table column headers, and all 3 employee modals (Add Staff, Assign Task, Edit Staff Member) now translate on language switch — titles, field labels, buttons. Added `emp_*`/`tbl_emp_*`/`task_*`/`btn_save_changes` keys to `en.py` + `ur.py`.
- **Assign Task redesigned**: instead of typing free-text, it now shows a dropdown of open (non-Delivered) orders labeled by **customer name** ("ORD-101 — Ayesha Khan (Kameez)"); picking one shows a read-only details panel (garment, status, order/delivery date, currently assigned tailor, total/advance/remaining) and auto-fills an editable task note — same pattern as the order card's customer auto-fill.
- Confirming now links **both** sides: sets the order's `tailor` field (new `_assign_order_tailor()` helper, mirrors the existing `quick_change_order_status()` pattern) and the employee's `current_task`/status (existing `update_employee_task()`, unchanged). Since the Dashboard's Active Orders Ledger reads `self.orders` live, the new tailor assignment shows up there immediately after reload — no dashboard code needed changing.

## Why
User: employee-section translation parity with the other screens, then: "connecting the employee section taking order from customer... by name... pop its details like order card... assign the work to it... linked to the main dashboard."

## Files touched
- `app/main_gui.py` (`apply_language_pack`, `open_add_employee_modal`, `open_assign_task_modal` rewritten, `edit_selected_employee`, new `_assign_order_tailor`)
- `app/lang/en.py`, `app/lang/ur.py`

## Verification
- pytest: 12/12. GUI smoke test: 23/23.
- Targeted script (14 checks, 13 pass — 1 "failure" was my own test's wrong assumption about pre-existing untranslated header casing, not an app bug): EN baseline, all UR translations for buttons/headers/3 modals, EN-restore.
- Targeted script (9/9 checks) for the Assign Task redesign: order dropdown shows customer names, selecting one auto-fills details + task note, saving writes the tailor to `orders.xlsx` and the task/status to `employees.xlsx`, and the Dashboard ledger shows the new tailor after reload.
