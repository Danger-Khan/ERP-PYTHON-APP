# 🧵 Jhagra Textile & Clothing — Atelier Ledger

An elegant, lightweight desktop management application for tailoring studios and apparel shops. Manages customer directory profiles, tailor measurement records, staff allocations, work assignments, order finances, and real-time shop floor execution metrics.

This desktop app uses a modern **soft-glassmorphism** design system — frosted-tint cards, soft borders, a light-catching top edge on every card, a blue/white/red accent strip, crisp typography, and an intuitive sidebar navigation layout, in both a light and a dark theme.

---

## ✨ Key Features

* **Soft-Glass Design System**: Frosted-tint cards, subtle borders, a light-catching top edge, and a blue/white/red brand accent strip — in both Light and Dark theme.
* **Visual Analytics Dashboard**:
  * Interactive donut gauges for **Work Done**, **In Progress**, and **Work Remaining**.
  * A finance snapshot row (Paid / Remaining / Debt) mirroring the Finance view.
  * Active orders ledger for Order IDs, customer names, garment types, status, and assigned tailors.
* **Finance**: a dedicated section tracking **Paid**, **Remaining** (unpaid, not yet delivered), and **Debt** (unpaid, already delivered) per order and shop-wide, backed by a small local SQLite ledger (`finance.db`, mirrored from `orders.xlsx`). Includes **All / Done / Due** filter tabs and an **Add Payment** tab to record a payment against any order with an outstanding balance.
* **Remembers where you left off**: theme, language, the sidebar section you were on, and window size/position are cached to disk and restored the next time the app opens.
* **Multilingual UI**: English and Urdu are fully translated (including RTL layout, section headers, buttons, and table headers); Pashto, Chinese, and Russian are selectable but currently fall back to English pending translation. Centralized translation files live under `app/lang`.
* **Customer Hub**:
  * Manage customer profiles, measurement cards, and address/contact details.
  * 1-click order creation from customer records.
* **Order Card**: a digital mirror of the paper order slip — garment type, style options, delivery, and payment, with customer measurements pulled automatically from the customer's saved record.
* **Staff & Task Allocation**:
  * Track employee roles and duty status.
  * Assign tasks by picking a real order (by customer name), which links the order's tailor and the employee's current task together and shows up on the Dashboard.
* **Diagnostics & Settings**:
  * Theme, language, garment types, and employee roles, all editable from one screen.
  * Stores application data in the `data/` folder (Excel) plus small SQLite/JSON caches (`finance.db`, `cache/app_state_cache.json`).
* **Real-time Header Clock**: Displays a live timestamp in the top header bar.

---

## 📁 Directory Structure

```text
app/
├── data/                   <-- Local Excel data storage, finance.db, session cache
├── models/                 <-- Data model definitions
├── routes/                 <-- Flask API route blueprints
├── security/                <-- Authentication and validation logic
├── services/                <-- Shared business logic and persistence helpers
├── tests/                   <-- Unit tests and smoke tests
├── utils/                   <-- finance_db.py, app_state.py, logger, excel_db, migrator
├── lang/                    <-- Per-language translation dictionaries (en, ur, ps, zh, ru)
├── changes/                 <-- Dated changelog entries (one or more per work session)
└── views/                   <-- Reusable Tkinter screen views

config.py                   <-- Application configuration
main_gui.py                 <-- Main Tkinter GUI entry point
run.py                      <-- Flask backend server entry point
README.md                   <-- This documentation file
readme.txt                  <-- Alternate plain-text summary
readme.me                   <-- Short-form summary
```

---

## 🚀 Getting Started

1. Create and activate your virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install flask flask-cors openpyxl bcrypt filelock reportlab
```

3. Run the desktop GUI:

```powershell
python main_gui.py
```

4. Run the Flask API backend (optional — the desktop GUI is fully self-contained on Excel/SQLite and does not require this):

```powershell
python run.py
```

---

## 🧪 Running Tests

To run all tests:

```powershell
python -m unittest discover -s app/tests
```

To run the GUI smoke test only (launches the real app against a throwaway temp data directory and drives it end-to-end):

```powershell
python app/tests/gui_smoke_test.py
```

---

## 🎨 Theme Reference

| Token | Light | Dark | Usage |
| --- | --- | --- | --- |
| `bg_body` | `#EEF2FA` | `#14151F` | Window backdrop |
| `bg_card` | `#FAFBFF` | `#20222E` | Card / section panels |
| `border` | `#DDE4F2` | `#33364A` | Soft card borders |
| Primary | `#007AFF` | same | Nav, primary actions, accent strip |
| Success | `#34C759` | same | Paid, done, ready |
| Warning | `#FF9500` | same | In progress, remaining |
| Danger | `#FF3B30` | same | Debt, delete, accent strip |

The top of the window carries a thin blue / white / red accent strip as a small brand signature above the header bar.

---

## 🔧 Notes

* Excel files are stored in `app/data/` by default; the finance ledger lives alongside them in `app/data/finance.db`, and the session cache in `app/data/cache/app_state_cache.json`.
* `config.py` defines paths for `DATA_DIR`, `BACKUP_DIR`, and `UPLOAD_DIR`.
* The app is intentionally built to use Excel-backed persistence for its records (customers/orders/employees) so it can run without a full SQL server; the Finance ledger and session cache are the two places it uses SQLite/JSON locally for numbers and preferences that benefit from being queried or reloaded directly.
