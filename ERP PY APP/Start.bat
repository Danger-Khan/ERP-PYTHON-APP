@echo off
:: Change directory to project root folder
cd /d "%~dp0"

:: Start Flask server silently in the background
start "" ".venv\Scripts\pythonw.exe" run.py

:: Start the Desktop GUI
start "" ".venv\Scripts\pythonw.exe" main_gui.py