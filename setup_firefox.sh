#!/bin/bash

# Firefox Setup Script for Njuskalo Scraper
# This script installs Firefox and updates the Python dependencies

echo "🦊 Setting up Firefox for Njuskalo Scraper"
echo "=========================================="

# Update package lists
echo "📦 Updating package lists..."
sudo apt-get update

# Install Firefox if not already installed
if ! command -v firefox &> /dev/null; then
    echo "🔧 Installing Firefox..."
    sudo apt-get install -y firefox
else
    echo "✅ Firefox is already installed"
    firefox --version
fi

# Install Firefox dependencies
echo "📦 Installing Firefox dependencies..."
sudo apt-get install -y \
    xvfb \
    x11-utils \
    x11-xserver-utils \
    dbus-x11 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    lsb-release \
    xdg-utils

# Activate virtual environment and install Python dependencies
echo "🐍 Installing Python dependencies..."
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  Virtual environment not found, installing globally"
fi

# Install updated requirements
pip install --upgrade pip
pip install -r requirements.txt

# Install geckodriver specifically
echo "🚗 Installing GeckoDriver..."
pip install geckodriver-autoinstaller

echo "🧪 Testing Firefox installation..."
if command -v firefox &> /dev/null; then
    echo "✅ Firefox installed: $(firefox --version)"
else
    echo "❌ Firefox installation failed"
    exit 1
fi

echo "🧪 Testing Python dependencies..."
python -c "
try:
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from webdriver_manager.firefox import GeckoDriverManager
    print('✅ All Selenium Firefox dependencies available')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"

echo "🎉 Firefox setup completed successfully!"
echo
echo "🚀 You can now run the scraper with Firefox:"
echo "   python njuskalo_scraper_with_tunnels.py --max-stores 3"
echo "   python njuskalo_sitemap_scraper.py"
echo "   ./run_scraper_with_tunnels.sh --max-stores 3"