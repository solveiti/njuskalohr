#!/bin/bash
"""
Remote Server User Setup Script

This script automates the creation of tunnel users on remote servers.
It sets up SSH keys, configures users, and installs necessary proxy software.
"""

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/server_setup.conf"
SSH_KEY_NAME="tunnel_key"
TUNNEL_USER="tunnel_user"
PROXY_PORT="8080"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
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
${BLUE}Remote Server User Setup Script${NC}

Usage: $0 [OPTIONS] <server-ip> [server-ip2] [server-ip3]...

OPTIONS:
    -u, --user <username>       SSH username for server access (default: root)
    -p, --port <port>           SSH port (default: 22)
    -k, --key <key-path>        SSH private key for server access
    -t, --tunnel-user <name>    Name for tunnel user (default: tunnel_user)
    -P, --proxy-port <port>     Proxy port to setup (default: 8080)
    --key-name <name>           SSH key name to generate (default: tunnel_key)
    --password                  Use password authentication instead of key
    --dry-run                   Show what would be done without executing
    -h, --help                  Show this help message

EXAMPLES:
    # Setup tunnel user on single server with root access
    $0 203.0.113.1

    # Setup on multiple servers with custom user
    $0 -u admin -k ~/.ssh/admin_key 203.0.113.1 203.0.113.2

    # Setup with custom tunnel user and proxy port
    $0 -t scraper_user -P 9090 203.0.113.1

    # Dry run to see what would be executed
    $0 --dry-run 203.0.113.1

REQUIREMENTS:
    - SSH access to target servers
    - sudo privileges on target servers
    - SSH key or password authentication
EOF
}

# Default values
SSH_USER="root"
SSH_PORT="22"
SSH_KEY="/home/srdjan/keys/connectvps"
USE_PASSWORD="false"
DRY_RUN="false"
SERVERS=(
    "178.18.253.123"
)

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -u|--user)
                SSH_USER="$2"
                shift 2
                ;;
            -p|--port)
                SSH_PORT="$2"
                shift 2
                ;;
            -k|--key)
                SSH_KEY="$2"
                shift 2
                ;;
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
            --password)
                USE_PASSWORD="true"
                shift
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
                SERVERS+=("$1")
                shift
                ;;
        esac
    done

    if [ ${#SERVERS[@]} -eq 0 ]; then
        error "At least one server IP/hostname must be provided"
    fi
}

# Generate SSH key pair if not exists
generate_ssh_keys() {
    local key_path="${SCRIPT_DIR}/${SSH_KEY_NAME}"

    if [[ -f "${key_path}" ]]; then
        log "SSH key ${key_path} already exists"
        return 0
    fi

    log "Generating SSH key pair: ${SSH_KEY_NAME}"

    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would generate SSH key: ssh-keygen -t rsa -b 4096 -f ${key_path} -N ''"
        return 0
    fi

    ssh-keygen -t rsa -b 4096 -f "${key_path}" -N '' -C "tunnel-key-$(date +%Y%m%d)"

    if [[ $? -eq 0 ]]; then
        log "SSH key pair generated successfully"
        chmod 600 "${key_path}"
        chmod 644 "${key_path}.pub"
    else
        error "Failed to generate SSH key pair"
    fi
}

# Create setup script for remote execution
create_remote_setup_script() {
    local script_content=$(cat << 'REMOTE_SCRIPT'
#!/bin/bash
# Remote server setup script

set -e

TUNNEL_USER="$1"
PROXY_PORT="$2"
SSH_PUBLIC_KEY="$3"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[REMOTE]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[REMOTE]${NC} $1"
}

error() {
    echo -e "${RED}[REMOTE]${NC} $1"
    exit 1
}

# Check if we need sudo or are already root
check_privileges() {
    if [[ $EUID -eq 0 ]]; then
        # We are root, no sudo needed
        SUDO_CMD=""
        log "Running as root user"
    else
        # We are not root, check if sudo is available and configured
        if command -v sudo >/dev/null 2>&1; then
            # Test if sudo works without password
            if sudo -n true 2>/dev/null; then
                SUDO_CMD="sudo"
                log "Using sudo for privilege escalation"
            else
                error "sudo requires password, but no terminal available. Please configure passwordless sudo or run as root user."
            fi
        else
            error "sudo not available and not running as root. Please install sudo or run as root user."
        fi
    fi
}

# Function to run commands with appropriate privileges
run_privileged() {
    if [[ -n "$SUDO_CMD" ]]; then
        $SUDO_CMD "$@"
    else
        "$@"
    fi
}

# Initialize privilege checking
check_privileges

# Update system packages
log "Updating system packages..."
if command -v apt-get >/dev/null 2>&1; then
    run_privileged apt-get update
    run_privileged apt-get install -y openssh-server curl wget software-properties-common
elif command -v yum >/dev/null 2>&1; then
    run_privileged yum update -y
    run_privileged yum install -y openssh-server curl wget
elif command -v dnf >/dev/null 2>&1; then
    run_privileged dnf update -y
    run_privileged dnf install -y openssh-server curl wget
else
    warn "Unknown package manager, manual installation may be required"
fi

# Create tunnel user
log "Creating tunnel user: ${TUNNEL_USER}"
if id "$TUNNEL_USER" &>/dev/null; then
    warn "User ${TUNNEL_USER} already exists"
else
    run_privileged useradd -m -s /bin/bash "$TUNNEL_USER"
    log "User ${TUNNEL_USER} created successfully"
fi

# Setup SSH directory and authorized_keys
USER_HOME="/home/${TUNNEL_USER}"
SSH_DIR="${USER_HOME}/.ssh"
AUTHORIZED_KEYS="${SSH_DIR}/authorized_keys"

log "Setting up SSH access for ${TUNNEL_USER}"
run_privileged mkdir -p "$SSH_DIR"
echo "$SSH_PUBLIC_KEY" | run_privileged tee "$AUTHORIZED_KEYS" > /dev/null
run_privileged chown -R "${TUNNEL_USER}:${TUNNEL_USER}" "$SSH_DIR"
run_privileged chmod 700 "$SSH_DIR"
run_privileged chmod 600 "$AUTHORIZED_KEYS"

# Configure SSH settings
log "Configuring SSH settings"
SSH_CONFIG="/etc/ssh/sshd_config"

# Backup original config
run_privileged cp "$SSH_CONFIG" "${SSH_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"

# Enable necessary SSH features
if ! run_privileged grep -q "^AllowTcpForwarding yes" "$SSH_CONFIG"; then
    echo "AllowTcpForwarding yes" | run_privileged tee -a "$SSH_CONFIG" > /dev/null
fi

if ! run_privileged grep -q "^GatewayPorts no" "$SSH_CONFIG"; then
    echo "GatewayPorts no" | run_privileged tee -a "$SSH_CONFIG" > /dev/null
fi

if ! run_privileged grep -q "^ClientAliveInterval" "$SSH_CONFIG"; then
    echo "ClientAliveInterval 60" | run_privileged tee -a "$SSH_CONFIG" > /dev/null
fi

if ! run_privileged grep -q "^ClientAliveCountMax" "$SSH_CONFIG"; then
    echo "ClientAliveCountMax 3" | run_privileged tee -a "$SSH_CONFIG" > /dev/null
fi

# Restart SSH service
log "Restarting SSH service"
if run_privileged systemctl is-active --quiet sshd; then
    run_privileged systemctl restart sshd
elif run_privileged systemctl is-active --quiet ssh; then
    run_privileged systemctl restart ssh
else
    run_privileged service ssh restart || run_privileged service sshd restart
fi

# Install and configure 3proxy (lightweight proxy server)
log "Installing 3proxy for SOCKS proxy"
PROXY_DIR="/opt/3proxy"
PROXY_CONFIG="${PROXY_DIR}/3proxy.cfg"

if [[ ! -d "$PROXY_DIR" ]]; then
    run_privileged mkdir -p "$PROXY_DIR"
    cd /tmp

    # Download and install 3proxy
    if command -v wget >/dev/null 2>&1; then
        wget -q https://github.com/z3APA3A/3proxy/archive/0.9.4.tar.gz -O 3proxy.tar.gz
    else
        curl -sL https://github.com/z3APA3A/3proxy/archive/0.9.4.tar.gz -o 3proxy.tar.gz
    fi

    tar -xzf 3proxy.tar.gz
    cd 3proxy-0.9.4

    # Compile 3proxy
    if command -v gcc >/dev/null 2>&1 || command -v make >/dev/null 2>&1; then
        make -f Makefile.Linux
        run_privileged cp bin/3proxy "$PROXY_DIR/"
    else
        # Try to get pre-compiled binary
        warn "Compiler not available, attempting to get pre-compiled binary"
        # This would need to be adapted based on available binaries
    fi
fi

# Create 3proxy configuration
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

# SOCKS5 proxy on specified port
socks -p${PROXY_PORT}
EOF

# Create systemd service for 3proxy
run_privileged tee /etc/systemd/system/3proxy.service > /dev/null << EOF
[Unit]
Description=3proxy lightweight proxy server
Documentation=https://github.com/z3APA3A/3proxy
After=network.target
Wants=network.target

[Service]
Type=forking
PIDFile=/var/run/3proxy.pid
ExecStartPre=/bin/rm -f /var/run/3proxy.pid
ExecStart=${PROXY_DIR}/3proxy ${PROXY_CONFIG}
ExecReload=/bin/kill -HUP \$MAINPID
ExecStop=/bin/kill -TERM \$MAINPID
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

# Start and enable 3proxy service
if [[ -f "${PROXY_DIR}/3proxy" ]]; then
    # Set proper permissions and ownership
    run_privileged chown root:root "${PROXY_DIR}/3proxy"
    run_privileged chmod 755 "${PROXY_DIR}/3proxy"
    run_privileged chown root:root "${PROXY_CONFIG}"
    run_privileged chmod 644 "${PROXY_CONFIG}"

    # Create log file with proper permissions
    run_privileged touch /var/log/3proxy.log
    run_privileged chown nobody:nogroup /var/log/3proxy.log
    run_privileged chmod 644 /var/log/3proxy.log

    # Clean up any existing PID file
    run_privileged rm -f /var/run/3proxy.pid

    # Start the service
    run_privileged systemctl daemon-reload
    run_privileged systemctl enable 3proxy
    run_privileged systemctl start 3proxy

    if run_privileged systemctl is-active --quiet 3proxy; then
        log "3proxy SOCKS server started successfully on port ${PROXY_PORT}"
    else
        warn "Failed to start 3proxy service"
        warn "Check service status with: systemctl status 3proxy"
        warn "Check logs with: journalctl -xeu 3proxy"
    fi
else
    warn "3proxy binary not available, proxy server not configured"
fi

# Configure firewall (if present)
log "Configuring firewall rules"
if command -v ufw >/dev/null 2>&1; then
    # UFW (Ubuntu)
    run_privileged ufw allow ssh
    run_privileged ufw allow from 127.0.0.1 to any port "${PROXY_PORT}"
    echo "y" | run_privileged ufw enable || true
elif command -v firewall-cmd >/dev/null 2>&1; then
    # FirewallD (CentOS/RHEL/Fedora)
    run_privileged firewall-cmd --permanent --add-service=ssh
    run_privileged firewall-cmd --permanent --add-port="${PROXY_PORT}/tcp" --source=127.0.0.1
    run_privileged firewall-cmd --reload
elif command -v iptables >/dev/null 2>&1; then
    # iptables
    run_privileged iptables -A INPUT -p tcp --dport 22 -j ACCEPT
    run_privileged iptables -A INPUT -s 127.0.0.1 -p tcp --dport "${PROXY_PORT}" -j ACCEPT
    run_privileged iptables -A INPUT -p tcp --dport "${PROXY_PORT}" -j DROP

    # Save iptables rules
    if command -v iptables-save >/dev/null 2>&1; then
        run_privileged iptables-save > /etc/iptables/rules.v4 2>/dev/null || \
        run_privileged iptables-save > /etc/iptables.rules 2>/dev/null || true
    fi
fi

# Create status check script
run_privileged tee "/home/${TUNNEL_USER}/check_status.sh" > /dev/null << 'EOF'
#!/bin/bash
echo "=== Tunnel Server Status ==="
echo "Date: $(date)"
echo "User: $(whoami)"
echo "SSH Service: $(systemctl is-active sshd ssh 2>/dev/null || echo 'unknown')"
echo "Proxy Service: $(systemctl is-active 3proxy 2>/dev/null || echo 'not configured')"
echo "Proxy Port: $(ss -tlpn | grep ':PROXY_PORT ' || echo 'not listening')"
echo "Active Connections: $(ss -t | grep -c ESTAB || echo '0')"
echo "System Load: $(uptime)"
echo "Disk Usage: $(df -h / | tail -1)"
echo "Memory Usage: $(free -h | grep Mem)"
EOF

run_privileged sed -i "s/PROXY_PORT/${PROXY_PORT}/g" "/home/${TUNNEL_USER}/check_status.sh"
run_privileged chmod +x "/home/${TUNNEL_USER}/check_status.sh"
run_privileged chown "${TUNNEL_USER}:${TUNNEL_USER}" "/home/${TUNNEL_USER}/check_status.sh"

log "Remote server setup completed successfully!"
log "Tunnel user: ${TUNNEL_USER}"
log "SOCKS proxy port: ${PROXY_PORT}"
log "Status script: /home/${TUNNEL_USER}/check_status.sh"

REMOTE_SCRIPT
)

    echo "$script_content"
}

# Setup server function
setup_server() {
    local server="$1"

    log "Setting up server: ${server}"

    # Prepare SSH connection options
    local ssh_opts="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=yes -p ${SSH_PORT}"

    if [[ "$USE_PASSWORD" == "true" ]]; then
        ssh_opts+=" -o PasswordAuthentication=yes"
    elif [[ -n "$SSH_KEY" ]]; then
        ssh_opts+=" -i $SSH_KEY"
    fi

    # Read public key
    local public_key_path="${SCRIPT_DIR}/${SSH_KEY_NAME}.pub"
    if [[ ! -f "$public_key_path" ]]; then
        error "Public key not found: $public_key_path"
    fi

    local public_key_content=$(cat "$public_key_path")

    # Create and execute remote setup script
    local remote_script=$(create_remote_setup_script)

    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would execute remote setup on ${server}"
        log "[DRY RUN] SSH options: ${ssh_opts}"
        log "[DRY RUN] Would create tunnel user: ${TUNNEL_USER}"
        log "[DRY RUN] Would setup proxy on port: ${PROXY_PORT}"
        return 0
    fi

    log "Executing remote setup script on ${server}..."

    # Execute remote script via SSH
    echo "$remote_script" | ssh $ssh_opts "${SSH_USER}@${server}" \
        "bash -s -- '${TUNNEL_USER}' '${PROXY_PORT}' '${public_key_content}'"

    if [[ $? -eq 0 ]]; then
        log "Server ${server} setup completed successfully"

        # Test SSH connection with new user
        log "Testing tunnel user SSH access..."
        ssh -o ConnectTimeout=10 -o IdentitiesOnly=yes $ssh_opts -i "${SCRIPT_DIR}/${SSH_KEY_NAME}" \
            "${TUNNEL_USER}@${server}" "echo 'SSH access test successful'"

        if [[ $? -eq 0 ]]; then
            log "✅ SSH access test passed for ${TUNNEL_USER}@${server}"
        else
            warn "❌ SSH access test failed for ${TUNNEL_USER}@${server}"
        fi

    else
        error "Failed to setup server ${server}"
    fi
}

# Generate tunnel configuration
generate_tunnel_config() {
    local config_file="${SCRIPT_DIR}/ssh_tunnels.json"
    local temp_config=$(mktemp)

    log "Generating tunnel configuration: ${config_file}"

    # Start JSON structure
    cat > "$temp_config" << EOF
{
  "tunnels": {
EOF

    local first_server=true
    local port_counter=8081

    for server in "${SERVERS[@]}"; do
        if [[ "$first_server" == "false" ]]; then
            echo "," >> "$temp_config"
        fi
        first_server=false

        # Generate server name from IP/hostname
        local server_name=$(echo "$server" | sed 's/[^a-zA-Z0-9]/_/g')

        cat >> "$temp_config" << EOF
    "${server_name}": {
      "host": "${server}",
      "port": ${SSH_PORT},
      "username": "${TUNNEL_USER}",
      "private_key_path": "${SCRIPT_DIR}/${SSH_KEY_NAME}",
      "local_port": ${port_counter},
      "remote_host": "127.0.0.1",
      "remote_port": ${PROXY_PORT},
      "compression": true,
      "keep_alive": 60,
      "max_retries": 3
    }
EOF

        ((port_counter++))
    done

    cat >> "$temp_config" << EOF
  },
  "rotation": {
    "auto_rotate": true,
    "rotation_interval": 1800,
    "random_order": true
  }
}
EOF

    if [[ "$DRY_RUN" == "true" ]]; then
        log "[DRY RUN] Would create configuration file:"
        cat "$temp_config"
        rm "$temp_config"
        return 0
    fi

    mv "$temp_config" "$config_file"
    chmod 600 "$config_file"

    log "Tunnel configuration generated: ${config_file}"
}

# Create management scripts
create_management_scripts() {
    local script_dir="$SCRIPT_DIR"

    # Create quick connect script
    cat > "${script_dir}/tunnel_connect.sh" << EOF
#!/bin/bash
# Quick tunnel connection script
cd "\$(dirname "\$0")"
python3 ssh_tunnel_manager.py connect "\$1"
EOF

    # Create tunnel status script
    cat > "${script_dir}/tunnel_status.sh" << EOF
#!/bin/bash
# Tunnel status script
cd "\$(dirname "\$0")"
python3 ssh_tunnel_manager.py status
EOF

    # Create tunnel rotation script
    cat > "${script_dir}/tunnel_rotate.sh" << EOF
#!/bin/bash
# Tunnel rotation script
cd "\$(dirname "\$0")"
python3 ssh_tunnel_manager.py rotate
EOF

    chmod +x "${script_dir}/tunnel_connect.sh"
    chmod +x "${script_dir}/tunnel_status.sh"
    chmod +x "${script_dir}/tunnel_rotate.sh"

    log "Management scripts created in ${script_dir}/"
}

# Main execution
main() {
    log "🚀 Starting Remote Server Setup for SSH Tunneling"

    parse_args "$@"

    log "Configuration:"
    log "  Servers: ${SERVERS[*]}"
    log "  SSH User: ${SSH_USER}"
    log "  SSH Port: ${SSH_PORT}"
    log "  Tunnel User: ${TUNNEL_USER}"
    log "  Proxy Port: ${PROXY_PORT}"
    log "  SSH Key Name: ${SSH_KEY_NAME}"
    log "  Use Password: ${USE_PASSWORD}"
    log "  Dry Run: ${DRY_RUN}"

    # Generate SSH keys
    generate_ssh_keys

    # Setup each server
    for server in "${SERVERS[@]}"; do
        log "Processing server: ${server}"
        setup_server "$server"
    done

    # Generate tunnel configuration
    generate_tunnel_config

    # Create management scripts
    create_management_scripts

    log "🎉 Setup completed successfully!"
    log ""
    log "Next steps:"
    log "  1. Test tunnels: python3 ssh_tunnel_manager.py list"
    log "  2. Connect to tunnel: python3 ssh_tunnel_manager.py connect <server_name>"
    log "  3. Check status: python3 ssh_tunnel_manager.py status"
    log "  4. Rotate tunnels: python3 ssh_tunnel_manager.py rotate"
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi