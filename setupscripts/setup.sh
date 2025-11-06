#!/bin/bash

# Setup script for Njuskalo Sitemap Store Scraper
# This script installs Chrome browser and Python dependencies

echo "🏪 Njuskalo Sitemap Store Scraper Setup"
echo "======================================"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ Don't run this script as root/sudo"
   exit 1
fi

# Update package lists
echo "📦 Updating package lists..."
sudo apt update

# Install Chrome browser
echo "🌐 Installing Google Chrome..."
if ! command -v google-chrome &> /dev/null; then
    # Download Chrome
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
    sudo apt update
    sudo apt install -y google-chrome-stable
    echo "✅ Chrome installed successfully"
else
    echo "✅ Chrome already installed"
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv .venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
echo "🐍 Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
    echo "✅ Python dependencies installed"
else
    echo "❌ requirements.txt not found"
    exit 1
fi

# Test installation
echo "🧪 Testing installation..."
echo "Checking Chrome version:"
google-chrome --version

echo ""
echo "Checking Python packages:"
.venv/bin/pip list | grep -E "(selenium|pandas|openpyxl|requests|lxml|beautifulsoup4)"

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Usage:"
echo "  Run the scraper with: .venv/bin/python run_scraper.py"
echo "  Or make it executable: chmod +x run_scraper.py && ./run_scraper.py"
echo ""
echo "📋 What this scraper does:"
echo "  1. Downloads sitemap index from njuskalo.hr"
echo "  2. Finds and downloads store-related XML files"
echo "  3. Extracts store URLs (trgovina) from sitemaps"
echo "  4. Visits each store page to scrape information"
echo "  5. Checks for Auto Moto category (categoryId=2)"
echo "  6. Extracts store address and ad counts"
echo "  7. Saves results to Excel file"
echo ""
echo "🚀 To run the scraper:"
echo "   python run_scraper.py"
echo ""
echo "📚 For more information, see README.md"