#!/bin/bash

# Manual 3proxy Installation Script
# Run this if the main setup script failed

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

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
    exit 1
}

# Check privileges
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
        "root") "$@" ;;
        "sudo") sudo "$@" ;;
        "none") error "Need root or passwordless sudo access" ;;
    esac
}

echo -e "${BLUE}=== Manual 3proxy Installation ===${NC}"

PROXY_DIR="/opt/3proxy"
PROXY_CONFIG="${PROXY_DIR}/3proxy.cfg"
PROXY_PORT="8080"

# Create directory
log "Creating 3proxy directory..."
run_privileged mkdir -p "$PROXY_DIR"
cd /tmp

# Install build dependencies
log "Installing build dependencies..."
if command -v apt-get >/dev/null 2>&1; then
    run_privileged apt-get update
    run_privileged apt-get install -y build-essential wget
elif command -v yum >/dev/null 2>&1; then
    run_privileged yum groupinstall -y "Development Tools"
    run_privileged yum install -y wget
fi

# Download and compile 3proxy
log "Downloading 3proxy source..."
if command -v wget >/dev/null 2>&1; then
    wget -q https://github.com/z3APA3A/3proxy/archive/0.9.4.tar.gz -O 3proxy.tar.gz
else
    curl -sL https://github.com/z3APA3A/3proxy/archive/0.9.4.tar.gz -o 3proxy.tar.gz
fi

log "Extracting and compiling 3proxy..."
tar -xzf 3proxy.tar.gz
cd 3proxy-0.9.4

# Compile based on available tools
if command -v gcc >/dev/null 2>&1; then
    make -f Makefile.Linux
    run_privileged cp bin/3proxy "$PROXY_DIR/"
else
    error "No compiler found. Install build-essential or gcc"
fi

# Create configuration
log "Creating 3proxy configuration..."
run_privileged tee "$PROXY_CONFIG" > /dev/null << EOF
# 3proxy configuration for tunnel
nscache 65536
timeouts 1 5 30 60 180 1800 15 60
daemon
pidfile /var/run/3proxy.pid
log /var/log/3proxy.log D
logformat "- +_L%t.%. %N.%p %E %U %C:%c %R:%r %O %I %h %T"

# Allow connections from localhost only
allow * 127.0.0.1
deny *

# SOCKS5 proxy on port 8080
socks -p8080
EOF

# Create systemd service
log "Creating systemd service..."
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

# Set permissions
log "Setting up permissions..."
run_privileged chown root:root "${PROXY_DIR}/3proxy"
run_privileged chmod 755 "${PROXY_DIR}/3proxy"
run_privileged chown root:root "${PROXY_CONFIG}"
run_privileged chmod 644 "${PROXY_CONFIG}"

# Create log file
run_privileged touch /var/log/3proxy.log
run_privileged chown nobody:nogroup /var/log/3proxy.log
run_privileged chmod 644 /var/log/3proxy.log

# Start service
log "Starting 3proxy service..."
run_privileged systemctl daemon-reload
run_privileged systemctl enable 3proxy
run_privileged systemctl start 3proxy

# Check status
if run_privileged systemctl is-active --quiet 3proxy; then
    echo -e "${GREEN}✓ 3proxy installed and started successfully!${NC}"
    systemctl status 3proxy --no-pager

    # Test proxy
    log "Testing proxy connection..."
    if command -v curl >/dev/null 2>&1; then
        if timeout 5 curl --socks5 127.0.0.1:8080 http://httpbin.org/ip >/dev/null 2>&1; then
            echo -e "${GREEN}✓ SOCKS proxy is working!${NC}"
        else
            echo -e "${YELLOW}⚠ Proxy test failed - check firewall${NC}"
        fi
    fi
else
    error "Failed to start 3proxy service"
fi

echo -e "${GREEN}=== Installation Complete ===${NC}"