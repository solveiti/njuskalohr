# 🔧 How to Use the Tunnel-Enabled Scraper

## 🔍 Why Your Scraper Wasn't Using SSH Tunnels

**The Problem:** Your original scraper (`njuskalo_sitemap_scraper.py`) was not configured to use SOCKS proxy. The Chrome browser was connecting directly to the internet without routing traffic through your SSH tunnel.

**The Missing Piece:** Chrome needs the `--proxy-server=socks5://127.0.0.1:PORT` argument to use SOCKS proxy.

## ✅ The Solution

I've created `njuskalo_scraper_with_tunnels.py` which:

1. **Inherits from your existing scraper** - All your current functionality is preserved
2. **Adds SSH tunnel management** - Automatically starts/stops tunnels
3. **Configures Chrome proxy** - Routes all traffic through SOCKS proxy
4. **Includes error handling** - Falls back to direct connection if tunnels fail

## 🚀 Quick Setup

### Step 1: Update Configuration

Edit `tunnel_config.json` and replace `YOUR_SERVER_IP` with your actual server IP:

```bash
# Edit the config file
nano tunnel_config.json

# Change this line:
"host": "YOUR_SERVER_IP",
# To your actual server IP:
"host": "123.456.789.012",
```

### Step 2: Test SSH Connection

Make sure your SSH keys are set up:

```bash
# Test SSH connection
ssh -i ~/.ssh/tunnel_key tunnel_user@YOUR_SERVER_IP "echo 'SSH OK'"

# If this fails, run the setup script first:
./setup_integration.sh
```

### Step 3: Run Tunnel-Enabled Scraper

```bash
# Basic usage (with tunnels)
python njuskalo_scraper_with_tunnels.py

# Verbose mode to see tunnel status
python njuskalo_scraper_with_tunnels.py --verbose

# Test with limited stores
python njuskalo_scraper_with_tunnels.py --max-stores 5 --verbose

# Without tunnels (direct connection)
python njuskalo_scraper_with_tunnels.py --no-tunnels
```

## 📊 What You'll See

### With Tunnels Working:

```
🚀 Njuskalo Scraper with SSH Tunnel Support
============================================================
✅ Tunnel manager initialized with config: tunnel_config.json
🚇 Starting SSH tunnel: server1
✅ SSH tunnel active: server1 (SOCKS proxy on port 8081)
🌐 Browser configured to use SOCKS proxy: socks5://127.0.0.1:8081
🎉 SSH tunnel is active - traffic will be routed through remote server
🏪 Starting enhanced scraping with tunnel support...
```

### Without Tunnels (if tunnel fails):

```
⚠️ Tunnel config not found: tunnel_config.json
🔄 Continuing without tunnels...
🏪 Starting enhanced scraping with tunnel support...
```

## 🧪 Testing the Integration

### Test 1: Check Your IP

```bash
# Run this to see if IP rotation is working
python test_integration.py
```

### Test 2: Monitor Traffic

```bash
# In one terminal, monitor your tunnel
ssh tunnel_user@YOUR_SERVER_IP "sudo journalctl -fu 3proxy"

# In another terminal, run the scraper
python njuskalo_scraper_with_tunnels.py --max-stores 2 --verbose
```

### Test 3: Compare IPs

```bash
# Check your real IP
curl http://httpbin.org/ip

# Check IP through tunnel (should be different)
curl --socks5 127.0.0.1:8081 http://httpbin.org/ip
```

## 🔧 Advanced Usage

### Use Specific Tunnel

```bash
python njuskalo_scraper_with_tunnels.py --tunnel server1
```

### Custom Config File

```bash
python njuskalo_scraper_with_tunnels.py --tunnel-config my_tunnels.json
```

### Debug Mode

```bash
python njuskalo_scraper_with_tunnels.py --verbose --max-stores 1
```

## 🔍 Troubleshooting

### 1. Tunnel Connection Issues

```bash
# Check SSH connection
ssh -i ~/.ssh/tunnel_key tunnel_user@YOUR_SERVER_IP

# Check 3proxy status on server
ssh tunnel_user@YOUR_SERVER_IP "systemctl status 3proxy"
```

### 2. Proxy Not Working

```bash
# Test SOCKS proxy manually
curl --socks5 127.0.0.1:8081 http://httpbin.org/ip
```

### 3. Config Issues

```bash
# Validate your config
python -c "import json; print(json.load(open('tunnel_config.json')))"
```

## 📋 Migration from Old Scraper

To migrate from your old scraper to the tunnel-enabled version:

### Option 1: Direct Replacement

```bash
# Backup your old scraper
cp run_scraper.py run_scraper_old.py

# Use the new tunnel-enabled scraper
python njuskalo_scraper_with_tunnels.py
```

### Option 2: Update run_scraper.py

You can modify `run_scraper.py` to use the tunnel-enabled scraper:

```python
# Change this line in run_scraper.py:
from njuskalo_sitemap_scraper import NjuskaloSitemapScraper

# To this:
from njuskalo_scraper_with_tunnels import TunnelEnabledNjuskaloScraper as NjuskaloSitemapScraper
```

## 🎯 Expected Results

After using the tunnel-enabled scraper:

- ✅ **IP Rotation**: Your traffic appears to come from your server's IP
- ✅ **Anti-Detection**: Better protection from rate limiting
- ✅ **Reliability**: Automatic tunnel management and reconnection
- ✅ **Compatibility**: All existing features work exactly the same
- ✅ **Monitoring**: Detailed logging of tunnel status

The scraper will now route all traffic through your SSH tunnel, making it appear as if you're browsing from your remote server instead of your local machine!
