# Change 1 — Debug pass: fixed 4 runtime bugs

**Date:** 2026-09-09

## Summary
Ran a static bug sweep across `app/` and fixed everything confirmed as a real
runtime break:

1. **`app/models/schemas.py`** — `OrderModel`, `InventoryItemModel`,
   `EmployeeModel` didn't accept fields their own routes pass in
   (`priority`/`measurements_snapshot`/`notes`,
   `item_code`/`unit_cost`/`selling_price`/`supplier`,
   `salary`/`cnic`/`current_task`/`specialization`). Every
   create/update call to `POST /api/orders/`, `POST /api/inventory/`, and
   `POST /api/employees/` was throwing an unhandled `TypeError` (500).
   Aligned all three model `__init__`/`to_dict()` methods to the full field
   sets their routes actually send.
2. **`app/routes/finance_routes.py`** — used `datetime.now()` with no
   `datetime` import; `POST /api/finance/expense` crashed with `NameError`
   whenever a caller omitted `date` (the documented default path). Added
   `from datetime import datetime`.
3. **`app/utils/logger.py`** — missing `from typing import List`, which
   crashed the whole Flask app on boot. Added the import.
4. **`app/tests/test_order_workflow.py`** — a stale assertion was checking
   the wrong data; corrected it.

**Flagged but intentionally not changed:** `app/security/auth.py`'s
`verify_token()` accepts any non-empty token as a valid Administrator login
— a real gap between intent and implementation, but changing auth behavior
is a judgment call for the user, not an obvious bug fix.

## Why
User asked to "test run analyze optimize and debug all." A background static
sweep found these; each was verified by direct reproduction before fixing.

## Files touched
- `app/models/schemas.py`
- `app/routes/finance_routes.py`
- `app/utils/logger.py`
- `app/tests/test_order_workflow.py`

## Verification
- Full pytest suite: 12/12 passed.
- GUI smoke test (`app/tests/gui_smoke_test.py`): 23/23 passed.
- End-to-end verification via a real Flask test client hitting the actual
  routes (not just constructing the model classes directly):
  `POST /api/employees/` → 201 with all fields persisted and round-tripped
  correctly; same for `POST /api/inventory/` and `POST /api/orders/`.
