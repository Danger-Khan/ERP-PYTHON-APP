# Change 3 — Data incident: stray data folder corrupted by my own test scripts, restored

**Date:** 2026-09-09

## Summary
While verifying the change 1 API fixes with ad-hoc Flask test-client scripts,
a pre-existing quirk in this codebase (`app/utils/excel_db.py` imports
`Config` via `from config import Config` rather than `from app.config import
Config`, unlike most other files) meant my attempt to redirect those test
writes to a temp directory didn't fully take effect. The writes landed in a
second, stray `data/` folder at the project root
(`ERP PY APP\data\`, separate from the real one at `app\data\`), overwriting
`employees.xlsx`, `inventory.xlsx`, and `orders.xlsx` there with test data,
and creating a new `system_audit.log`.

The app's real data (`app\data\*.xlsx`, confirmed against what the GUI smoke
test seeds/expects) was never touched.

Restored `data\employees.xlsx`, `data\inventory.xlsx`, and `data\orders.xlsx`
from the pre-test backups that `ExcelDB._backup()` automatically saved into
`data\backups\` before each of my writes, and deleted the stray
`system_audit.log`. Confirmed with user before restoring.

## Why
Transparency: my own testing caused this, so it's logged like any other
change even though it's a data-integrity fix rather than a feature change.

## Files touched (restored, not newly modified)
- `data\employees.xlsx`
- `data\inventory.xlsx`
- `data\orders.xlsx`
- `data\system_audit.log` (deleted — didn't exist before)

## Verification
Read back all three restored files with openpyxl: confirmed 0 rows / blank
headers, matching their true pre-session state (this stray folder was
already unpopulated/unused before my session — the backups prove the
pre-existing content was blank, not that real data was lost).

## Lesson applied going forward
Sandbox live-testing more carefully — verify which `Config`/data-dir a test
script actually resolves to before writing, rather than assuming an override
took effect.
