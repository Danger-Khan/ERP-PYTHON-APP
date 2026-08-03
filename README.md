# 🧵 Jhagra Textile & Clothing — Atelier Ledger

An elegant, lightweight desktop management application for tailoring studios and apparel shops. Designed to manage customer directory profiles, tailor measurement records, staff allocations, work assignments, and real-time shop floor execution metrics.

This desktop app uses a modern **Apple Glassmorphic Light Theme** design system with crisp typography, soft pastel surfaces, and an intuitive sidebar navigation layout.

---

## ✨ Key Features

* **Apple Glass Light Design System**: Modern typography, subtle borders, soft backgrounds, and accent colors.
* **Visual Analytics Dashboard**:
  * Interactive donut gauges for **Work Done**, **In Progress**, and **Work Remaining**.
  * Active orders ledger for Order IDs, customer names, garment types, status, and assigned tailors.
* **Multilingual UI support**: English, Urdu, Pashto, Chinese, and Russian with centralized translation files under `app/lang`.
* **Customer Hub**:
  * Manage customer profiles and measurement cards.
  * 1-click order creation from customer records.
* **Staff & Task Allocation**:
  * Track employee roles and duty status.
  * Assign and persist daily tasks.
* **Diagnostics & Settings**:
  * Checks backend API connection and local Excel storage status.
  * Stores application state in the `data/` folder.
* **Real-time Header Clock**: Displays a live timestamp in the top header bar.

---

## 📁 Directory Structure

```text
app/
├── data/                   <-- Local Excel data storage
├── models/                 <-- Data model definitions
├── routes/                 <-- Flask API route blueprints
├── security/               <-- Authentication and validation logic
├── services/               <-- Shared business logic and persistence helpers
├── tests/                  <-- Unit tests and smoke tests
└── views/                  <-- Reusable Tkinter screen views

config.py                   <-- Application configuration
main_gui.py                 <-- Main Tkinter GUI entry point
run.py                      <-- Flask backend server entry point
README.md                   <-- This documentation file
readme.txt                  <-- Alternate plain-text summary
readme.me                   <-- Draft README content
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

4. Run the Flask API backend:

```powershell
python run.py
```

---

## 🧪 Running Tests

To run all tests:

```powershell
python -m unittest discover -s app/tests
```

To run the GUI smoke test only:

```powershell
python app/tests/gui_smoke_test.py
```

---

## 🔧 Notes

* Excel files are stored in `app/data/` by default.
* `config.py` defines paths for `DATA_DIR`, `BACKUP_DIR`, and `UPLOAD_DIR`.
* The app is intentionally built to use Excel-backed persistence so it can run without a full SQL database.
