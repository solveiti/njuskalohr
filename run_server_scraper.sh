#!/bin/bash
"""
Server-Compatible Scraper Runner

This script runs the enhanced Njuskalo scraper with xvfb-run for server compatibility.
It uses the server-optimized Firefox configuration that works on headless servers.

Usage:
    ./run_server_scraper.sh [--max-stores N] [--no-tunnels] [--verbose]
"""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Server-Compatible Njuskalo Scraper${NC}"
echo -e "${BLUE}===================================${NC}"

# Check if xvfb-run is available
if ! command -v xvfb-run &> /dev/null; then
    echo -e "${RED}❌ xvfb-run not found!${NC}"
    echo -e "${YELLOW}💡 Install with: sudo pacman -S xorg-server-xvfb${NC}"
    exit 1
fi

# Check if Firefox is installed
if ! command -v firefox &> /dev/null; then
    echo -e "${RED}❌ Firefox not found!${NC}"
    echo -e "${YELLOW}💡 Install with: sudo pacman -S firefox${NC}"
    exit 1
fi

# Check if GeckoDriver exists
if [ ! -f "/usr/local/bin/geckodriver" ]; then
    echo -e "${RED}❌ GeckoDriver not found at /usr/local/bin/geckodriver${NC}"
    echo -e "${YELLOW}💡 Make sure GeckoDriver is installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All dependencies found${NC}"
echo -e "${BLUE}🖥️  Starting scraper with xvfb-run...${NC}"

# Run the enhanced scraper with xvfb-run
xvfb-run -a python enhanced_tunnel_scraper.py "$@"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}🎉 Scraping completed successfully!${NC}"
else
    echo -e "${RED}❌ Scraping failed with exit code: $exit_code${NC}"
fi

exit $exit_code