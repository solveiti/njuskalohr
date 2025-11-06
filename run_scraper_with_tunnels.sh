#!/bin/bash

# SSH Tunnel Scraper Runner
# This script runs the Njuskalo scraper with SSH tunnel support

echo "🚀 Njuskalo Scraper with SSH Tunnels"
echo "===================================="

# Activate virtual environment
source .venv/bin/activate

# Check if tunnel configuration exists
if [ ! -f "tunnel_config.json" ]; then
    echo "❌ Error: tunnel_config.json not found"
    echo "💡 Make sure tunnel_config.json is in the current directory"
    exit 1
fi

# Check if SSH key exists
if [ ! -f "tunnel_key" ]; then
    echo "❌ Error: SSH private key 'tunnel_key' not found"
    echo "💡 Make sure your SSH private key is in the current directory"
    exit 1
fi

echo "✅ Configuration files found"
echo "📁 Config: tunnel_config.json"
echo "🔑 SSH Key: tunnel_key"
echo

# Default parameters
HEADLESS="--headless"
MAX_STORES=""
TUNNEL_CONFIG="--tunnel-config tunnel_config.json"
DATABASE="--no-database"  # Default to no database for testing
TUNNELS=""  # Default to using tunnels
VERBOSE=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --gui)
            HEADLESS=""
            echo "🖥️  Running with GUI (visible browser)"
            shift
            ;;
        --max-stores)
            MAX_STORES="--max-stores $2"
            echo "📊 Limited to $2 stores"
            shift 2
            ;;
        --database)
            DATABASE=""
            echo "💾 Database storage enabled"
            shift
            ;;
        --no-tunnels)
            TUNNELS="--no-tunnels"
            echo "🚫 Tunnels disabled"
            shift
            ;;
        --verbose)
            VERBOSE="--verbose"
            echo "🔍 Verbose logging enabled"
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo
            echo "Options:"
            echo "  --gui           Run with visible browser (default: headless)"
            echo "  --max-stores N  Limit scraping to N stores (for testing)"
            echo "  --database      Enable database storage (default: CSV only)"
            echo "  --no-tunnels    Disable SSH tunnel usage"
            echo "  --verbose       Enable verbose logging"
            echo "  --help          Show this help message"
            echo
            echo "Examples:"
            echo "  $0                           # Basic run with tunnels"
            echo "  $0 --max-stores 5           # Test with 5 stores"
            echo "  $0 --gui --verbose          # Visible browser with debug"
            echo "  $0 --no-tunnels             # Run without tunnels"
            exit 0
            ;;
        *)
            echo "❌ Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "🔧 Starting scraper with tunnels..."
echo "⏳ This may take a while depending on the number of stores..."
echo

# Run the scraper
python njuskalo_scraper_with_tunnels.py \
    $HEADLESS \
    $MAX_STORES \
    $TUNNEL_CONFIG \
    $DATABASE \
    $TUNNELS \
    $VERBOSE

echo
echo "🏁 Scraper execution completed"