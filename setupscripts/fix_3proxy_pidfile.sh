#!/bin/bash

# Fix 3proxy PID file issue on existing installations
# Run this script as root to fix PID file problems

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
    exit 1
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root"
fi

echo -e "${BLUE}=== Fixing 3proxy PID File Issue ===${NC}"
echo

PROXY_DIR="/opt/3proxy"
PROXY_CONFIG="$PROXY_DIR/3proxy.cfg"
PROXY_PORT="8080"

# Check if 3proxy is installed
if [[ ! -f "$PROXY_DIR/3proxy" ]]; then
    error "3proxy not found at $PROXY_DIR/3proxy. Run the setup script first."
fi

# Stop the service if running
log "Stopping 3proxy service..."
systemctl stop 3proxy 2>/dev/null || true

# Fix the 3proxy configuration (remove daemon and pidfile)
log "Fixing 3proxy configuration..."
cat > "$PROXY_CONFIG" << EOF
# 3proxy configuration for tunnel (fixed - no daemon mode)
nscache 65536
timeouts 1 5 30 60 180 1800 15 60
log /var/log/3proxy/3proxy.log
logformat "- +_L%t.%. %N.%p %E %U %C:%c %R:%r %O %I %h %T"

# Allow connections from localhost only
allow * 127.0.0.1
deny *

# SOCKS5 proxy on specified port
socks -p$PROXY_PORT
EOF

# Fix the systemd service (change to simple type, no PID file)
log "Fixing systemd service configuration..."
cat > /etc/systemd/system/3proxy.service << 'EOF'
[Unit]
Description=3proxy lightweight proxy server
Documentation=https://github.com/z3APA3A/3proxy
After=network.target
Wants=network.target

[Service]
Type=simple
ExecStart=/opt/3proxy/3proxy /opt/3proxy/3proxy.cfg
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
Restart=on-failure
RestartSec=5
User=nobody
Group=nogroup

# Security settings
NoNewPrivileges=true
PrivateDevices=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/3proxy

[Install]
WantedBy=multi-user.target
EOF

# Clean up any existing PID files
log "Cleaning up PID files..."
rm -f /var/run/3proxy.pid

# Set proper permissions
log "Setting proper permissions..."
chown root:root "$PROXY_DIR/3proxy"
chmod 755 "$PROXY_DIR/3proxy"
chown root:root "$PROXY_CONFIG"
chmod 644 "$PROXY_CONFIG"

# Ensure log file exists with proper permissions
log "Setting up log directory..."
mkdir -p /var/log/3proxy
chown nobody:nogroup /var/log/3proxy
chmod 755 /var/log/3proxy

touch /var/log/3proxy/3proxy.log
chown nobody:nogroup /var/log/3proxy/3proxy.log
chmod 644 /var/log/3proxy/3proxy.log

# Reload and restart service
log "Restarting 3proxy service..."
systemctl daemon-reload
systemctl enable 3proxy
systemctl start 3proxy

# Check if service is running
sleep 2
if systemctl is-active --quiet 3proxy; then
    echo -e "${GREEN}✓ 3proxy service is now running successfully!${NC}"
    systemctl status 3proxy --no-pager -l
    echo

    # Test the proxy
    log "Testing SOCKS proxy..."
    if command -v curl >/dev/null 2>&1; then
        if timeout 5 curl --socks5 127.0.0.1:$PROXY_PORT http://httpbin.org/ip >/dev/null 2>&1; then
            echo -e "${GREEN}✓ SOCKS proxy is working correctly!${NC}"
        else
            warn "SOCKS proxy test failed - check firewall settings"
        fi
    else
        warn "curl not available for proxy testing"
    fi
else
    error "3proxy service failed to start after fixes"
    echo "Service status:"
    systemctl status 3proxy --no-pager -l
    echo
    echo "Recent logs:"
    journalctl -xeu 3proxy --no-pager -n 10
    exit 1
fi

echo
echo -e "${GREEN}=== Fix Complete ===${NC}"
echo "3proxy is now running without PID file dependency."
echo "You can check the status with: systemctl status 3proxy"
echo "View logs with: journalctl -fu 3proxy"