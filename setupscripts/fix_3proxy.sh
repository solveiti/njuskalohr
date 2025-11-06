#!/bin/bash

# 3proxy Service Diagnostics and Fix Script
# This script diagnoses and fixes common 3proxy service issues

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

# Check if running as root or with sudo
check_privileges() {
    if [ "$EUID" -eq 0 ]; then
        echo "root"
    elif sudo -n true 2>/dev/null; then
        echo "sudo"
    else
        echo "none"
    fi
}

run_privileged() {
    local privilege_level=$(check_privileges)

    case "$privilege_level" in
        "root")
            "$@"
            ;;
        "sudo")
            sudo "$@"
            ;;
        "none")
            error "Insufficient privileges to run: $*"
            error "This script requires either root access or passwordless sudo privileges"
            exit 1
            ;;
    esac
}

echo -e "${BLUE}=== 3proxy Service Diagnostics ===${NC}"
echo

# 1. Check if 3proxy service exists
log "Checking 3proxy service status..."
if systemctl list-unit-files | grep -q "3proxy.service"; then
    echo "✓ 3proxy service file exists"
else
    error "3proxy service file not found. Run the setup script first."
    exit 1
fi

# 2. Check service status
log "Current service status:"
systemctl status 3proxy.service --no-pager || true
echo

# 3. Check systemd logs
log "Recent systemd logs for 3proxy:"
journalctl -xeu 3proxy.service --no-pager -n 20 || true
echo

# 4. Check if 3proxy binary exists and is executable
PROXY_DIR="/opt/3proxy"
PROXY_BINARY="${PROXY_DIR}/3proxy"
PROXY_CONFIG="${PROXY_DIR}/3proxy.cfg"

log "Checking 3proxy binary..."
if [[ -f "$PROXY_BINARY" ]]; then
    echo "✓ 3proxy binary exists at $PROXY_BINARY"
    if [[ -x "$PROXY_BINARY" ]]; then
        echo "✓ 3proxy binary is executable"
    else
        warn "3proxy binary is not executable"
        log "Making 3proxy binary executable..."
        run_privileged chmod +x "$PROXY_BINARY"
    fi
else
    error "3proxy binary not found at $PROXY_BINARY"
    error "Run the setup script to install 3proxy"
    exit 1
fi

# 5. Check configuration file
log "Checking 3proxy configuration..."
if [[ -f "$PROXY_CONFIG" ]]; then
    echo "✓ 3proxy configuration exists at $PROXY_CONFIG"
    echo "Configuration content:"
    cat "$PROXY_CONFIG"
    echo
else
    error "3proxy configuration not found at $PROXY_CONFIG"
    exit 1
fi

# 6. Check permissions and ownership
log "Checking file permissions..."
ls -la "$PROXY_DIR"/ || true
echo

# 7. Check if required directories and files are accessible
log "Checking required directories..."
for dir in "/var/run" "/var/log"; do
    if [[ -d "$dir" && -w "$dir" ]]; then
        echo "✓ $dir is writable"
    else
        warn "$dir is not writable"
    fi
done

# 8. Check if port is available
PROXY_PORT=$(grep -o 'socks -p[0-9]*' "$PROXY_CONFIG" | grep -o '[0-9]*' || echo "8080")
log "Checking if port $PROXY_PORT is available..."
if netstat -tulpn 2>/dev/null | grep -q ":$PROXY_PORT "; then
    warn "Port $PROXY_PORT is already in use:"
    netstat -tulpn | grep ":$PROXY_PORT " || true
else
    echo "✓ Port $PROXY_PORT is available"
fi

# 9. Test 3proxy binary manually
log "Testing 3proxy binary manually..."
if "$PROXY_BINARY" -v 2>/dev/null; then
    echo "✓ 3proxy binary runs and reports version"
else
    error "3proxy binary fails to run"
    error "Check if all dependencies are installed"
fi

echo
echo -e "${BLUE}=== Attempting Fixes ===${NC}"

# Fix 1: Ensure proper permissions
log "Setting correct permissions..."
run_privileged chown root:root "$PROXY_BINARY"
run_privileged chmod 755 "$PROXY_BINARY"
run_privileged chown root:root "$PROXY_CONFIG"
run_privileged chmod 644 "$PROXY_CONFIG"

# Fix 2: Create improved systemd service file
log "Creating improved systemd service file..."
run_privileged tee /etc/systemd/system/3proxy.service > /dev/null << 'EOF'
[Unit]
Description=3proxy lightweight proxy server
Documentation=https://github.com/z3APA3A/3proxy
After=network.target
Wants=network.target

[Service]
Type=forking
PIDFile=/var/run/3proxy.pid
ExecStartPre=/bin/rm -f /var/run/3proxy.pid
ExecStart=/opt/3proxy/3proxy /opt/3proxy/3proxy.cfg
ExecReload=/bin/kill -HUP $MAINPID
ExecStop=/bin/kill -TERM $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=5
User=nobody
Group=nogroup

# Security settings
NoNewPrivileges=true
PrivateDevices=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/run /var/log

[Install]
WantedBy=multi-user.target
EOF

# Fix 3: Ensure log directory permissions
log "Setting up log directory permissions..."
run_privileged touch /var/log/3proxy.log
run_privileged chown nobody:nogroup /var/log/3proxy.log
run_privileged chmod 644 /var/log/3proxy.log

# Fix 4: Clean up any existing PID file
log "Cleaning up PID file..."
run_privileged rm -f /var/run/3proxy.pid

# Fix 5: Reload systemd and restart service
log "Reloading systemd and restarting service..."
run_privileged systemctl daemon-reload
run_privileged systemctl stop 3proxy 2>/dev/null || true
sleep 2
run_privileged systemctl start 3proxy

# Check final status
echo
log "Final service status check..."
if run_privileged systemctl is-active --quiet 3proxy; then
    echo -e "${GREEN}✓ 3proxy service is now running successfully!${NC}"
    systemctl status 3proxy.service --no-pager -l
    echo
    log "Testing SOCKS proxy connection..."
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
    echo "Latest logs:"
    journalctl -xeu 3proxy.service --no-pager -n 10
    exit 1
fi

echo
echo -e "${GREEN}=== Diagnostics and Fixes Complete ===${NC}"
echo "3proxy service should now be working correctly."
echo "You can check the status anytime with: systemctl status 3proxy"
echo "View logs with: journalctl -fu 3proxy"