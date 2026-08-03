Jhagra Textile & Clothing — Atelier Ledger

A lightweight Tkinter desktop application for managing tailoring orders, customer measurement profiles, staff assignments, and shop floor analytics.

The app uses Excel-backed persistence and a modern Apple-style UI with smooth dashboards, order ledger tables, and customer management.

Supports multilingual UI using centralized translation files in `app/lang` for English, Urdu, Pashto, Chinese, and Russian.

Key Features:
- Apple Glass Light UI with clean panels and accent buttons.
- Dashboard analytics with progress donut gauges.
- Customer hub with contact details and measurement cards.
- Staff and task allocation for tailors and shop workers.
- Order cards with garment types, measurements, style options, delivery, and payment.
- Built-in local Excel data storage and optional PDF receipt generation.

Project Layout:
- `app/`: Application code and modules.
- `app/data/`: Local Excel storage files.
- `app/models/`: Data models.
- `app/routes/`: Flask API blueprints.
- `app/security/`: Authentication and validation logic.
- `app/services/`: Shared business logic.
- `app/tests/`: Unit tests and GUI smoke tests.
- `app/views/`: Reusable Tkinter views.
- `config.py`: App configuration for data and backup directories.
- `main_gui.py`: Main desktop GUI entry point.
- `run.py`: Flask backend server.
- `app/README.md`: Markdown documentation.

Getting Started:
1. Create the virtual environment:
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
2. Install dependencies:
   pip install flask flask-cors openpyxl bcrypt filelock reportlab
3. Run the desktop app:
   python main_gui.py
4. Run the backend server:
   python run.py

Testing:
- Run all tests:
  python -m unittest discover -s app/tests
- Run GUI smoke test only:
  python app/tests/gui_smoke_test.py

Notes:
- Excel files are stored under `app/data/`.
- `config.py` defines `DATA_DIR`, `BACKUP_DIR`, and `UPLOAD_DIR`.
- `app/README.md` contains the detailed Markdown documentation.
