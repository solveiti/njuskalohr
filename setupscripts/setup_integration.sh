#!/bin/bash

# Quick Setup Script for 3proxy Integration
# This script helps you configure SSH keys and test the connection

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $1"
    exit 1
}

echo -e "${BLUE}🔧 3proxy Integration Setup${NC}"
echo "This script will help you set up SSH keys and test your 3proxy connection"
echo

# Configuration
SSH_KEY_PATH="$HOME/.ssh/tunnel_key"
SERVER_IP=""
TUNNEL_USER="tunnel_user"

# Step 1: Get server IP
read -p "Enter your server IP address: " SERVER_IP
if [[ -z "$SERVER_IP" ]]; then
    error "Server IP is required"
fi

echo
log "Configuration:"
log "  Server: $TUNNEL_USER@$SERVER_IP"
log "  SSH Key: $SSH_KEY_PATH"
echo

# Step 2: Generate SSH key if needed
if [[ ! -f "$SSH_KEY_PATH" ]]; then
    log "Generating SSH key pair..."
    ssh-keygen -t rsa -b 4096 -f "$SSH_KEY_PATH" -N '' -C "scraper-tunnel-$(date +%Y%m%d)"
    log "SSH key generated: $SSH_KEY_PATH"
else
    log "SSH key already exists: $SSH_KEY_PATH"
fi

# Step 3: Display public key
echo
log "Your public key (copy this to your server):"
echo -e "${YELLOW}$(cat "${SSH_KEY_PATH}.pub")${NC}"
echo

# Step 4: Instructions for server setup
echo -e "${BLUE}📋 Server Setup Instructions:${NC}"
echo "Run these commands on your server (as root):"
echo
echo -e "${YELLOW}# Switch to tunnel user${NC}"
echo "sudo su - $TUNNEL_USER"
echo
echo -e "${YELLOW}# Create SSH directory${NC}"
echo "mkdir -p ~/.ssh"
echo "chmod 700 ~/.ssh"
echo
echo -e "${YELLOW}# Add your public key${NC}"
echo "echo '$(cat "${SSH_KEY_PATH}.pub")' >> ~/.ssh/authorized_keys"
echo "chmod 600 ~/.ssh/authorized_keys"
echo "exit"
echo

# Step 5: Wait for user confirmation
read -p "Press Enter after you've added the public key to your server..."

# Step 6: Test SSH connection
log "Testing SSH connection..."
if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o IdentityFile=no "$SSH_KEY_PATH" "$TUNNEL_USER@$SERVER_IP" "echo 'SSH connection successful'"; then
    log "✅ SSH connection test passed!"
else
    error "❌ SSH connection test failed. Please check your server configuration."
fi

# Step 7: Test server status
log "Checking server status..."
if ssh -i "$SSH_KEY_PATH" "$TUNNEL_USER@$SERVER_IP" "./check_status.sh"; then
    log "✅ Server status check passed!"
else
    warn "⚠️ Could not get server status (check_status.sh might not exist)"
fi

# Step 8: Create tunnel configuration
log "Creating tunnel configuration file..."
cat > tunnel_config.json << EOF
{
    "servers": [
        {
            "name": "server1",
            "host": "$SERVER_IP",
            "port": 22,
            "username": "$TUNNEL_USER",
            "private_key_path": "$SSH_KEY_PATH",
            "local_port": 8081,
            "remote_host": "127.0.0.1",
            "remote_port": 8080
        }
    ],
    "rotation_enabled": true,
    "health_check_interval": 30,
    "auto_reconnect": true
}
EOF

log "✅ Tunnel configuration saved to: tunnel_config.json"

# Step 9: Create simple test script
log "Creating quick test script..."
cat > quick_test.py << 'EOF'
#!/usr/bin/env python3
"""Quick test script for 3proxy tunnel"""

import requests
import subprocess
import time
import sys

def test_tunnel():
    SERVER_IP = sys.argv[1] if len(sys.argv) > 1 else input("Enter server IP: ")

    # Start tunnel
    print("Starting tunnel...")
    cmd = f"ssh -D 8081 -f -C -q -N -o IdentitiesOnly=yes -o StrictHostKeyChecking=no -i ~/.ssh/tunnel_key tunnel_user@{SERVER_IP}"
    subprocess.run(cmd, shell=True)
    time.sleep(3)

    try:
        # Test proxy
        proxies = {'http': 'socks5://127.0.0.1:8081', 'https': 'socks5://127.0.0.1:8081'}
        response = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=10)

        if response.status_code == 200:
            ip_data = response.json()
            print(f"✅ SUCCESS! Proxy IP: {ip_data['origin']}")
        else:
            print("❌ Proxy test failed")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Clean up
        subprocess.run("pkill -f 'ssh -D 8081'", shell=True)
        print("Tunnel stopped")

if __name__ == "__main__":
    test_tunnel()
EOF

chmod +x quick_test.py
log "✅ Quick test script created: quick_test.py"

echo
echo -e "${GREEN}🎉 Setup completed successfully!${NC}"
echo
echo -e "${BLUE}Next steps:${NC}"
echo "1. Run the integration test:"
echo "   python test_integration.py"
echo
echo "2. Quick tunnel test:"
echo "   python quick_test.py $SERVER_IP"
echo
echo "3. Update your scraper to use SOCKS proxy:"
echo "   proxy_url = 'socks5://127.0.0.1:8081'"
echo
echo "4. Use the tunnel configuration:"
echo "   tunnel_config.json contains your server settings"
echo
echo -e "${YELLOW}💡 Pro tip:${NC} Test everything with test_integration.py before using in production!"