# 🧵 Jhagra Textile & Clothing — Atelier Ledger

An elegant, lightweight desktop management application for tailoring studios and apparel shops. Designed to manage customer directory profiles, tailor measurement records, staff allocations, work assignments, and real-time shop floor execution metrics.

Redesigned with a modern **Apple Glassmorphic Light Theme** design system featuring crisp typography, high contrast, smooth canvas-rendered progress gauges, and an intuitive sidebar navigation layout.

---

## ✨ Key Features

* **🍏 Apple Glass Light Design System**: Built with modern system typography (`SF Pro Text` / `Segoe UI`), subtle borders (`#E5E5EA`), soft background tones (`#F5F5F7`), and iOS accent colors.
* **📊 Visual Analytics Dashboard**:
  * **Interactive Donut Gauges**: Canvas-rendered percentage indicators for **Work Done**, **In Progress**, and **Work Remaining**.
  * **Active Orders Ledger**: Quick-view table tracking Order IDs, customer names, garment types, status, and assigned tailors.
* **👤 Customer Hub**:
  * Comprehensive customer directory storing contact details and complete garment measurement profiles (length, chest, waist, shoulder, collar, arm length).
  * 1-click order creation directly from customer records.
* **📋 Staff & Task Allocation**:
  * Track employee roles (Master Cutter, Stitching Specialist, Press & Finishing).
  * Track duty status (**On Duty** vs **Off Duty**) and assign prioritized bench tasks.
* **⚙️ Diagnostics & Settings**:
  * Shop branding preferences & localization settings.
  * System diagnostics view checking backend Flask API connection, `./data` storage path status, and OpenPyXL Excel engine status.
* **⏰ Real-time Header Clock**: Live system timestamp updated every second in the top header bar.

---

## 📁 Directory Structure

```text
ERP Website/
├── data/                   <-- All Excel databases (.xlsx) stored here
│   ├── customers.xlsx
│   ├── employees.xlsx
│   └── orders.xlsx
├── app/                    <-- Flask Backend API code
│   ├── routes/
│   ├── security/
│   └── utils/
├── main_gui.py             # Main Desktop Tkinter GUI Application
├── run.py                  # Backend Flask Server Entry Point
├── start_atelier.bat       # 1-Click Launch Script
└── README.md               # Project Documentation