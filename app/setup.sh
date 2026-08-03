#!/bin/bash

# Exit script immediately on error
set -e

echo "========================================================"
echo " 🚀 One-Click System Update & Python Dependency Setup"
echo "========================================================"

# 1. Update & Upgrade OS Packages (Ubuntu / Debian / WSL)
if command -v apt-get &> /dev/null; then
    echo "📦 [1/4] Updating package repositories..."
    sudo apt-get update -y

    echo "⬆️ [2/4] Upgrading installed system packages..."
    sudo apt-get upgrade -y

    echo "🔧 Installing Python build essentials..."
    sudo apt-get install -y python3 python3-pip python3-venv build-essential libffi-dev
else
    echo "ℹ️ Skipping OS-level package upgrades (Not running Debian/Ubuntu apt)."
fi

# 2. Upgrade core Python packaging tools
echo "🐍 [3/4] Upgrading pip, setuptools, and wheel..."
python3 -m pip install --upgrade pip setuptools wheel

# 3. Install Project & Common Python Dependencies
echo "📚 [4/4] Installing Atelier Project & Common Python Libraries..."
python3 -m pip install \
    flask \
    flask-cors \
    openpyxl \
    bcrypt \
    filelock \
    requests \
    python-dotenv \
    pillow \
    pandas \
    numpy \
    pytest \
    gunicorn \
    werkzeug

echo "========================================================"
echo " 🎉 ALL UPDATES & DEPENDENCIES INSTALLED SUCCESSFULLY!"
echo "========================================================"