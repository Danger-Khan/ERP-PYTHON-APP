Jhagra Textile & Clothing — Atelier Ledger

A lightweight Tkinter desktop application for managing tailoring orders, customer measurement profiles, staff assignments, order finances, and shop floor analytics.

The app uses Excel-backed persistence for its records, a small local SQLite ledger for finance figures, and a soft-glassmorphism UI with frosted-tint cards, a blue/white/red accent strip, dashboards, order ledger tables, and customer management — in both a Light and a Dark theme.

Supports a multilingual UI using centralized translation files in `app/lang`. English and Urdu are fully translated; Pashto, Chinese, and Russian are selectable but currently fall back to English.

Key Features:
- Soft-glass UI with frosted cards, soft borders, and a blue/white/red accent strip.
- Dashboard analytics with progress donut gauges and a finance snapshot (Paid/Remaining/Debt).
- Finance section: Paid, Remaining, and Debt per order and shop-wide, with All/Done/Due filter tabs and an Add Payment form, backed by a local SQLite ledger (finance.db).
- Remembers theme, language, last open section, and window size/position between sessions.
- Customer hub with contact details, address, and measurement cards.
- Staff and task allocation for tailors and shop workers, linked to real orders.
- Order cards with garment types, measurements, style options, delivery, and payment.
- Built-in local Excel data storage and optional PDF receipt generation.

Project Layout:
- `app/`: Application code and modules.
- `app/data/`: Local Excel storage, finance.db, and the session cache.
- `app/models/`: Data models.
- `app/routes/`: Flask API blueprints.
- `app/security/`: Authentication and validation logic.
- `app/services/`: Shared business logic.
- `app/utils/`: finance_db.py, app_state.py, and other local persistence helpers.
- `app/lang/`: Translation dictionaries per language.
- `app/changes/`: Dated changelog entries.
- `app/tests/`: Unit tests and GUI smoke tests.
- `app/views/`: Reusable Tkinter views.
- `config.py`: App configuration for data and backup directories.
- `main_gui.py`: Main desktop GUI entry point.
- `run.py`: Flask backend server (optional; the desktop app does not require it).
- `app/README.md`: Markdown documentation.

Getting Started:
1. Create the virtual environment:
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
2. Install dependencies:
   pip install flask flask-cors openpyxl bcrypt filelock reportlab
3. Run the desktop app:
   python main_gui.py
4. Run the backend server (optional):
   python run.py

Testing:
- Run all tests:
  python -m unittest discover -s app/tests
- Run GUI smoke test only:
  python app/tests/gui_smoke_test.py

Notes:
- Excel files are stored under `app/data/`; the finance ledger is `app/data/finance.db`, and the session cache is `app/data/cache/app_state_cache.json`.
- `config.py` defines `DATA_DIR`, `BACKUP_DIR`, and `UPLOAD_DIR`.
- `app/README.md` contains the detailed Markdown documentation.
