#!/bin/bash

# SSH Tunnel Installation Script for Remote Servers
# This script installs and configures SSH tunnels on remote Ubuntu/Debian servers
# using SSH key-based authentication

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/tunnel_config.txt"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_rsa}"
SSH_USER="${SSH_USER:-root}"

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if SSH key exists
check_ssh_key() {
    if [ ! -f "$SSH_KEY" ]; then
        print_error "SSH key not found at: $SSH_KEY"
        print_info "Please specify SSH key path using: export SSH_KEY=/path/to/key"
        exit 1
    fi
    print_info "Using SSH key: $SSH_KEY"
}

# Function to test SSH connection
test_ssh_connection() {
    local host=$1
    local user=$2

    print_info "Testing SSH connection to $user@$host..."
    if ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o BatchMode=yes -o StrictHostKeyChecking=no "$user@$host" "echo 2>&1" &>/dev/null; then
        print_info "SSH connection successful"
        return 0
    else
        print_error "Failed to connect to $user@$host"
        return 1
    fi
}

# Function to install autossh on remote server
install_autossh() {
    local host=$1
    local user=$2

    print_info "Installing autossh on $host..."

    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$user@$host" bash <<'ENDSSH'
        set -e

        # Update package list
        echo "Updating package list..."
        sudo apt-get update -qq

        # Install autossh (for persistent tunnels)
        if ! command -v autossh &> /dev/null; then
            echo "Installing autossh..."
            sudo apt-get install -y autossh
        else
            echo "autossh is already installed"
        fi

        # Install screen (for managing tunnel sessions)
        if ! command -v screen &> /dev/null; then
            echo "Installing screen..."
            sudo apt-get install -y screen
        else
            echo "screen is already installed"
        fi

        echo "Installation completed successfully"
ENDSSH

    if [ $? -eq 0 ]; then
        print_info "autossh installed successfully on $host"
        return 0
    else
        print_error "Failed to install autossh on $host"
        return 1
    fi
}

# Function to create systemd service for persistent tunnel
create_tunnel_service() {
    local host=$1
    local user=$2
    local local_port=$3
    local remote_host=$4
    local remote_port=$5
    local tunnel_type=$6  # "local" or "remote"
    local service_name="ssh-tunnel-${local_port}"

    print_info "Creating systemd service for tunnel on $host..."

    # Determine tunnel direction
    if [ "$tunnel_type" = "local" ]; then
        tunnel_args="-L ${local_port}:${remote_host}:${remote_port}"
        description="SSH Local Tunnel: localhost:${local_port} -> ${remote_host}:${remote_port}"
    else
        tunnel_args="-R ${remote_port}:${remote_host}:${local_port}"
        description="SSH Remote Tunnel: remote:${remote_port} -> ${remote_host}:${local_port}"
    fi

    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$user@$host" bash <<ENDSSH
        set -e

        # Create systemd service file
        sudo tee /etc/systemd/system/${service_name}.service > /dev/null <<'EOF'
[Unit]
Description=${description}
After=network.target

[Service]
Type=simple
User=${user}
ExecStart=/usr/bin/autossh -M 0 -N ${tunnel_args} \\
    -o ServerAliveInterval=30 \\
    -o ServerAliveCountMax=3 \\
    -o StrictHostKeyChecking=no \\
    -o ExitOnForwardFailure=yes \\
    ${remote_host}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

        # Reload systemd and enable service
        sudo systemctl daemon-reload
        sudo systemctl enable ${service_name}.service

        echo "Service ${service_name} created and enabled"
ENDSSH

    if [ $? -eq 0 ]; then
        print_info "Tunnel service created successfully on $host"
        return 0
    else
        print_error "Failed to create tunnel service on $host"
        return 1
    fi
}

# Function to start tunnel service
start_tunnel_service() {
    local host=$1
    local user=$2
    local service_name=$3

    print_info "Starting tunnel service on $host..."

    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$user@$host" \
        "sudo systemctl start ${service_name} && sudo systemctl status ${service_name} --no-pager" || true
}

# Function to create a manual tunnel (non-persistent)
create_manual_tunnel() {
    local host=$1
    local user=$2
    local local_port=$3
    local remote_host=$4
    local remote_port=$5
    local tunnel_type=$6

    print_info "Creating manual tunnel on $host..."

    if [ "$tunnel_type" = "local" ]; then
        tunnel_cmd="ssh -i $SSH_KEY -f -N -L ${local_port}:${remote_host}:${remote_port} $user@$host"
        print_info "Local tunnel: localhost:${local_port} -> ${remote_host}:${remote_port} (via $host)"
    else
        tunnel_cmd="ssh -i $SSH_KEY -f -N -R ${remote_port}:${remote_host}:${local_port} $user@$host"
        print_info "Remote tunnel: $host:${remote_port} -> ${remote_host}:${local_port}"
    fi

    print_info "Command: $tunnel_cmd"
    eval "$tunnel_cmd"
}

# Function to show usage
show_usage() {
    cat <<EOF
SSH Tunnel Installation Script

Usage: $0 [OPTIONS]

Options:
    -h, --help              Show this help message
    -s, --server HOST       Remote server hostname or IP
    -u, --user USER         SSH user (default: $SSH_USER)
    -k, --key PATH          Path to SSH private key (default: $SSH_KEY)
    -c, --config FILE       Use configuration file for batch installation

    Tunnel Configuration (for single server):
    -l, --local-port PORT   Local port to forward
    -r, --remote-port PORT  Remote port to forward to
    -t, --target HOST       Target host (default: localhost)
    -m, --mode MODE         Tunnel mode: 'local' or 'remote' (default: local)
    -p, --persistent        Create persistent tunnel using systemd

Environment Variables:
    SSH_KEY                 Path to SSH private key
    SSH_USER                Default SSH user

Examples:
    # Install autossh on a single server
    $0 -s 192.168.1.100 -u admin

    # Create local persistent tunnel (forward port 8080 to remote port 80)
    $0 -s 192.168.1.100 -l 8080 -r 80 -p

    # Create remote tunnel (expose local port 3000 on remote port 8000)
    $0 -s 192.168.1.100 -l 3000 -r 8000 -m remote -p

    # Batch installation from config file
    $0 -c tunnel_config.txt

Configuration file format (tunnel_config.txt):
    server_host,ssh_user,local_port,remote_host,remote_port,tunnel_type,persistent
    192.168.1.100,admin,8080,localhost,80,local,yes
    192.168.1.101,admin,3000,localhost,8000,remote,yes

EOF
}

# Main function
main() {
    local server=""
    local user="$SSH_USER"
    local local_port=""
    local remote_port=""
    local target_host="localhost"
    local tunnel_mode="local"
    local persistent=false
    local use_config=false
    local config_file=""

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -s|--server)
                server="$2"
                shift 2
                ;;
            -u|--user)
                user="$2"
                shift 2
                ;;
            -k|--key)
                SSH_KEY="$2"
                shift 2
                ;;
            -l|--local-port)
                local_port="$2"
                shift 2
                ;;
            -r|--remote-port)
                remote_port="$2"
                shift 2
                ;;
            -t|--target)
                target_host="$2"
                shift 2
                ;;
            -m|--mode)
                tunnel_mode="$2"
                shift 2
                ;;
            -p|--persistent)
                persistent=true
                shift
                ;;
            -c|--config)
                use_config=true
                config_file="$2"
                shift 2
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # Check SSH key
    check_ssh_key

    # Process configuration file if specified
    if [ "$use_config" = true ]; then
        if [ ! -f "$config_file" ]; then
            print_error "Configuration file not found: $config_file"
            exit 1
        fi

        print_info "Processing configuration file: $config_file"

        while IFS=',' read -r srv usr lport rhost rport tmode persist; do
            # Skip comments and empty lines
            [[ "$srv" =~ ^#.*$ ]] && continue
            [[ -z "$srv" ]] && continue

            print_info "=== Processing server: $srv ==="

            # Test connection
            if ! test_ssh_connection "$srv" "$usr"; then
                print_warn "Skipping $srv due to connection failure"
                continue
            fi

            # Install autossh
            install_autossh "$srv" "$usr"

            # Create tunnel if ports are specified
            if [ -n "$lport" ] && [ -n "$rport" ]; then
                if [ "$persist" = "yes" ]; then
                    create_tunnel_service "$srv" "$usr" "$lport" "$rhost" "$rport" "$tmode"
                    start_tunnel_service "$srv" "$usr" "ssh-tunnel-${lport}"
                else
                    create_manual_tunnel "$srv" "$usr" "$lport" "$rhost" "$rport" "$tmode"
                fi
            fi

            print_info "=== Completed: $srv ==="
            echo ""
        done < "$config_file"

        print_info "Batch installation completed!"
        exit 0
    fi

    # Single server mode
    if [ -z "$server" ]; then
        print_error "Server hostname or IP is required"
        show_usage
        exit 1
    fi

    # Test SSH connection
    if ! test_ssh_connection "$server" "$user"; then
        exit 1
    fi

    # Install autossh
    install_autossh "$server" "$user"

    # Create tunnel if ports are specified
    if [ -n "$local_port" ] && [ -n "$remote_port" ]; then
        if [ "$persistent" = true ]; then
            create_tunnel_service "$server" "$user" "$local_port" "$target_host" "$remote_port" "$tunnel_mode"
            start_tunnel_service "$server" "$user" "ssh-tunnel-${local_port}"
        else
            create_manual_tunnel "$server" "$user" "$local_port" "$target_host" "$remote_port" "$tunnel_mode"
        fi
    fi

    print_info "Installation completed successfully!"
}

# Run main function
main "$@"
