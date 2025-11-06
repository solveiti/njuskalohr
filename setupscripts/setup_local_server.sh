#!/bin/bash
"""
Local Server Setup Script for SSH Tunneling

This script is designed to be run directly on the server as root user.
It sets up tunnel users, SSH configuration, and proxy software locally.
"""

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TUNNEL_USER="tunnel_user"
PROXY_PORT="8080"
SSH_KEY_NAME="tunnel_key"

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
    exit 1
}

# Function to show usage
show_usage() {
    cat << EOF
${BLUE}Local Server Setup Script for SSH Tunneling${NC}

This script must be run directly on the target server as root user.

Usage: $0 [OPTIONS]

OPTIONS:
    -t, --tunnel-user <name>    Name for tunnel user (default: tunnel_user)
    -P, --proxy-port <port>     Proxy port to setup (default: 8080)
    --key-name <name>           SSH key name to generate (default: tunnel_key)
    --public-key <key>          Public key content to add for tunnel user
    --public-key-file <file>    File containing public key to add
    --dry-run                   Show what would be done without executing
    -h, --help                  Show this help message

EXAMPLES:
    # Basic setup with default settings
    $0

    # Setup with custom tunnel user and proxy port
    $0 -t scraper_user -P 9090

    # Setup with existing public key
    $0 --public-key-file /path/to/public_key.pub

    # Dry run to see what would be executed
    $0 --dry-run

REQUIREMENTS:
    - Must be run as root user
    - Server should have internet access for package installation
    - Standard package managers (apt/yum/dnf) available

This script will:
    1. Create a dedicated tunnel user
    2. Configure SSH access for the tunnel user
    3. Install and configure 3proxy SOCKS server
    4. Configure firewall rules
    5. Set up system services
EOF
}

# Default values
DRY_RUN="false"
PUBLIC_KEY=""
PUBLIC_KEY_FILE=""

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--tunnel-user)
                TUNNEL_USER="$2"
                shift 2
                ;;
            -P|--proxy-port)
                PROXY_PORT="$2"
                shift 2
                ;;
            --key-name)
                SSH_KEY_NAME="$2"
                shift 2
                ;;
            --public-key)
                PUBLIC_KEY="$2"
                shift 2
                ;;
            --public-key-file)
                PUBLIC_KEY_FILE="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            -*)
                error "Unknown option: $1"
                ;;
            *)
                error "Unexpected argument: $1"
                ;;
        esac
    done
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root user"
    fi
}

# Detect operating system
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
    elif [[ -f /etc/redhat-release ]]; then
        OS="rhel"
    elif [[ -f /etc/debian_version ]]; then
        OS="debian"
    else
        OS="unknown"
    fi

    log "Detected OS: $OS"
}

# Install required packages
install_packages() {
    log "Installing required packages..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would install packages based on OS: $OS"
        return 0
    fi

    case "$OS" in
        ubuntu|debian)
            apt-get update
            apt-get install -y wget curl build-essential openssh-server ufw
            ;;
        centos|rhel|fedora)
            if command -v dnf >/dev/null 2>&1; then
                dnf groupinstall -y "Development Tools"
                dnf install -y wget curl openssh-server firewalld
            else
                yum groupinstall -y "Development Tools"
                yum install -y wget curl openssh-server
            fi
            ;;
        *)
            error "Unsupported operating system: $OS"
            ;;
    esac
}

# Create tunnel user
create_tunnel_user() {
    log "Creating tunnel user: ${TUNNEL_USER}"

    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would create user: $TUNNEL_USER"
        log "[DRY RUN] Would set up home directory and SSH access"
        return 0
    fi

    # Check if user already exists
    if id "$TUNNEL_USER" &>/dev/null; then
        warn "User $TUNNEL_USER already exists"
    else
        # Create user with home directory
        useradd -m -s /bin/bash "$TUNNEL_USER"
        log "Created user: $TUNNEL_USER"
    fi

    # Set up user directories
    local user_home="/home/$TUNNEL_USER"
    local ssh_dir="$user_home/.ssh"

    mkdir -p "$ssh_dir"
    chmod 700 "$ssh_dir"
    chown "$TUNNEL_USER:$TUNNEL_USER" "$ssh_dir"
}

# Setup SSH access for tunnel user
setup_ssh_access() {
    log "Setting up SSH access for ${TUNNEL_USER}"

    local user_home="/home/$TUNNEL_USER"
    local ssh_dir="$user_home/.ssh"
    local authorized_keys="$ssh_dir/authorized_keys"

    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would setup SSH authorized_keys"
        return 0
    fi

    # Handle public key input
    local key_content=""
    if [[ -n "$PUBLIC_KEY" ]]; then
        key_content="$PUBLIC_KEY"
    elif [[ -n "$PUBLIC_KEY_FILE" ]]; then
        if [[ -f "$PUBLIC_KEY_FILE" ]]; then
            key_content=$(cat "$PUBLIC_KEY_FILE")
        else
            error "Public key file not found: $PUBLIC_KEY_FILE"
        fi
    else
        warn "No public key provided. SSH access will need to be configured manually."
        return 0
    fi

    # Add public key to authorized_keys
    echo "$key_content" > "$authorized_keys"
    chmod 600 "$authorized_keys"
    chown "$TUNNEL_USER:$TUNNEL_USER" "$authorized_keys"

    log "SSH access configured for $TUNNEL_USER"
}

# Configure SSH server
configure_ssh() {
    log "Configuring SSH server"

    local ssh_config="/etc/ssh/sshd_config"

    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would configure SSH server settings"
        return 0
    fi

    # Backup original config
    if [[ -f "$ssh_config" ]]; then
        cp "$ssh_config" "${ssh_config}.backup.$(date +%Y%m%d_%H%M%S)"
    fi

    # Configure SSH settings for security and tunneling
    cat >> "$ssh_config" << EOF

# SSH Tunnel Configuration
AllowUsers root $TUNNEL_USER
PermitTunnel yes
GatewayPorts no
X11Forwarding no
AllowAgentForwarding yes
AllowTcpForwarding yes
ClientAliveInterval 60
ClientAliveCountMax 3
EOF

    # Restart SSH service
    systemctl restart sshd || systemctl restart ssh
    log "SSH server configured and restarted"
}

# Install and configure 3proxy
install_3proxy() {
    log "Installing 3proxy for SOCKS proxy"

    local proxy_dir="/opt/3proxy"
    local proxy_config="$proxy_dir/3proxy.cfg"

    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would install and configure 3proxy"
        return 0
    fi

    # Create directory
    mkdir -p "$proxy_dir"
    cd /tmp

    # Download and install 3proxy
    log "Downloading 3proxy source..."
    if command -v wget >/dev/null 2>&1; then
        wget -q https://github.com/z3APA3A/3proxy/archive/0.9.4.tar.gz -O 3proxy.tar.gz
    elif command -v curl >/dev/null 2>&1; then
        curl -sL https://github.com/z3APA3A/3proxy/archive/0.9.4.tar.gz -o 3proxy.tar.gz
    else
        error "Neither wget nor curl available for downloading 3proxy"
    fi

    tar -xzf 3proxy.tar.gz
    cd 3proxy-0.9.4

    # Compile 3proxy
    log "Compiling 3proxy..."
    if command -v gcc >/dev/null 2>&1; then
        make -f Makefile.Linux
        cp bin/3proxy "$proxy_dir/"
    else
        error "GCC compiler not found. Install build-essential or gcc."
    fi

    # Create 3proxy configuration
    log "Creating 3proxy configuration..."
    cat > "$proxy_config" << EOF
# 3proxy configuration for tunnel
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

    # Create systemd service
    log "Creating systemd service for 3proxy..."
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

    # Set proper permissions
    chown root:root "$proxy_dir/3proxy"
    chmod 755 "$proxy_dir/3proxy"
    chown root:root "$proxy_config"
    chmod 644 "$proxy_config"

    # Create log directory and file with proper permissions
    mkdir -p /var/log/3proxy
    chown nobody:nogroup /var/log/3proxy
    chmod 755 /var/log/3proxy

    touch /var/log/3proxy/3proxy.log
    chown nobody:nogroup /var/log/3proxy/3proxy.log
    chmod 644 /var/log/3proxy/3proxy.log

    # Start and enable service
    systemctl daemon-reload
    systemctl enable 3proxy
    systemctl start 3proxy

    if systemctl is-active --quiet 3proxy; then
        log "3proxy SOCKS server started successfully on port $PROXY_PORT"
    else
        error "Failed to start 3proxy service"
    fi
}

# Configure firewall
configure_firewall() {
    log "Configuring firewall rules"

    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would configure firewall rules"
        return 0
    fi

    case "$OS" in
        ubuntu|debian)
            if command -v ufw >/dev/null 2>&1; then
                # UFW (Ubuntu)
                ufw allow ssh
                ufw allow from 127.0.0.1 to any port "$PROXY_PORT"
                echo "y" | ufw enable || true
                log "UFW firewall configured"
            fi
            ;;
        centos|rhel|fedora)
            if command -v firewall-cmd >/dev/null 2>&1; then
                # FirewallD (CentOS/RHEL/Fedora)
                systemctl enable firewalld
                systemctl start firewalld
                firewall-cmd --permanent --add-service=ssh
                firewall-cmd --permanent --add-rich-rule="rule family='ipv4' source address='127.0.0.1' port protocol='tcp' port='$PROXY_PORT' accept"
                firewall-cmd --reload
                log "FirewallD configured"
            fi
            ;;
    esac
}

# Create status check script
create_status_script() {
    log "Creating status check script"

    local status_script="/home/$TUNNEL_USER/check_status.sh"

    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would create status check script"
        return 0
    fi

    cat > "$status_script" << EOF
#!/bin/bash
echo "=== Tunnel Server Status ==="
echo "Date: \$(date)"
echo "Hostname: \$(hostname)"
echo "Uptime: \$(uptime -p)"
echo
echo "=== Services ==="
echo "SSH Service: \$(systemctl is-active sshd ssh 2>/dev/null || echo 'unknown')"
echo "3proxy Service: \$(systemctl is-active 3proxy 2>/dev/null || echo 'unknown')"
echo
echo "=== Network ==="
echo "Public IP: \$(curl -s ifconfig.me 2>/dev/null || echo 'unknown')"
echo "SOCKS Proxy Port $PROXY_PORT: \$(netstat -tlnp 2>/dev/null | grep ':$PROXY_PORT ' | wc -l) listener(s)"
echo
echo "=== System Resources ==="
echo "CPU Usage: \$(top -bn1 | grep "Cpu(s)" | awk '{print \$2}' | cut -d'%' -f1)"
echo "Memory Usage: \$(free | grep Mem | awk '{printf("%.1f%%", \$3/\$2 * 100.0)}')"
echo "Disk Usage: \$(df -h / | awk 'NR==2{printf "%s", \$5}')"
EOF

    chmod +x "$status_script"
    chown "$TUNNEL_USER:$TUNNEL_USER" "$status_script"
    log "Status script created at $status_script"
}

# Display setup summary
show_summary() {
    echo
    echo -e "${BLUE}=== Setup Summary ===${NC}"
    echo -e "${GREEN}✓ Tunnel user created: $TUNNEL_USER${NC}"
    echo -e "${GREEN}✓ SSH server configured${NC}"
    echo -e "${GREEN}✓ 3proxy SOCKS server running on port: $PROXY_PORT${NC}"
    echo -e "${GREEN}✓ Firewall configured${NC}"
    echo -e "${GREEN}✓ Status check script created${NC}"
    echo
    echo -e "${BLUE}=== Connection Information ===${NC}"
    echo "SSH Tunnel Command:"
    echo "  ssh -D 8081 -f -C -q -N -o IdentitiesOnly=yes $TUNNEL_USER@$(hostname -I | awk '{print $1}')"
    echo
    echo "SOCKS Proxy Endpoint:"
    echo "  127.0.0.1:$PROXY_PORT (via SSH tunnel)"
    echo
    echo "Status Check:"
    echo "  ssh $TUNNEL_USER@$(hostname -I | awk '{print $1}') './check_status.sh'"
    echo
    echo -e "${YELLOW}Note: Make sure to configure SSH key authentication for the tunnel user${NC}"
}

# Main execution
main() {
    echo -e "${BLUE}Local Server Setup Script for SSH Tunneling${NC}"
    echo "This script will set up this server for SSH tunneling with SOCKS proxy"
    echo

    parse_args "$@"
    check_root
    detect_os

    log "Starting local server setup..."
    log "Tunnel user: $TUNNEL_USER"
    log "Proxy port: $PROXY_PORT"

    if [[ "$DRY_RUN" == "true" ]]; then
        warn "DRY RUN MODE - No actual changes will be made"
    fi

    install_packages
    create_tunnel_user
    setup_ssh_access
    configure_ssh
    install_3proxy
    configure_firewall
    create_status_script

    if [[ "$DRY_RUN" != "true" ]]; then
        show_summary
    else
        log "[DRY RUN] Setup completed (no changes made)"
    fi

    log "Local server setup completed successfully!"
}

# Run main function with all arguments
main "$@"