#!/bin/bash

# Firefox Setup Script for Manjaro/Arch Linux
# This script installs Firefox and updates the Python dependencies

echo "🦊 Setting up Firefox for Manjaro/Arch Linux"
echo "============================================="

# Update package database
echo "📦 Updating package database..."
sudo pacman -Sy

# Install Firefox if not already installed
if ! command -v firefox &> /dev/null; then
    echo "🔧 Installing Firefox..."
    sudo pacman -S --noconfirm firefox
else
    echo "✅ Firefox is already installed"
    firefox --version
fi

# Install required system dependencies
echo "📦 Installing system dependencies..."
sudo pacman -S --noconfirm \
    xorg-server-xvfb \
    gtk3 \
    dbus \
    libx11 \
    libxcomposite \
    libxcursor \
    libxdamage \
    libxext \
    libxfixes \
    libxi \
    libxrandr \
    libxrender \
    libxss \
    libxtst \
    ca-certificates \
    ttf-liberation \
    alsa-lib \
    at-spi2-atk \
    mesa \
    gtk3 \
    nspr \
    nss

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

# Fix the requirements.txt to use correct geckodriver version
sed -i 's/geckodriver-autoinstaller>=2.1.0/geckodriver-autoinstaller>=0.1.0/' requirements.txt

pip install -r requirements.txt

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
echo "   python run_scraper.py"
echo "   ./run_scraper_with_tunnels.sh --max-stores 3"