#!/usr/bin/env python3
"""
Remote Server User Setup Script (Python Version)

Advanced script for setting up tunnel users on remote servers with enhanced features.
Supports bulk deployment, configuration validation, and health monitoring.
"""

import os
import sys
import json
import time
import logging
import argparse
import subprocess
import threading
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import tempfile
import socket
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('server_setup.log')
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ServerConfig:
    """Configuration for a remote server"""
    host: str
    ssh_port: int = 22
    ssh_user: str = "root"
    ssh_key: Optional[str] = None
    use_password: bool = False
    tunnel_user: str = "tunnel_user"
    proxy_port: int = 8080
    name: Optional[str] = None

    def __post_init__(self):
        if self.name is None:
            # Generate name from host
            self.name = self.host.replace('.', '_').replace('-', '_')

@dataclass
class SetupResult:
    """Result of server setup operation"""
    server: str
    success: bool
    message: str
    execution_time: float
    ssh_test_passed: bool = False
    proxy_test_passed: bool = False

class RemoteServerManager:
    """Manages remote server setup and configuration"""

    def __init__(self, script_dir: str = None):
        self.script_dir = Path(script_dir) if script_dir else Path(__file__).parent
        self.ssh_key_name = "tunnel_key"
        self.results: List[SetupResult] = []

    def generate_ssh_keys(self, key_name: str = None) -> bool:
        """Generate SSH key pair if not exists"""
        if key_name:
            self.ssh_key_name = key_name

        key_path = self.script_dir / self.ssh_key_name

        if key_path.exists():
            logger.info(f"SSH key {key_path} already exists")
            return True

        logger.info(f"Generating SSH key pair: {self.ssh_key_name}")

        try:
            subprocess.run([
                'ssh-keygen', '-t', 'rsa', '-b', '4096',
                '-f', str(key_path), '-N', '',
                '-C', f'tunnel-key-{datetime.now().strftime("%Y%m%d")}'
            ], check=True, capture_output=True)

            # Set proper permissions
            os.chmod(key_path, 0o600)
            os.chmod(f"{key_path}.pub", 0o644)

            logger.info("SSH key pair generated successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to generate SSH key: {e}")
            return False

    def create_remote_setup_script(self, config: ServerConfig) -> str:
        """Create the remote setup script"""

        # Read public key
        pub_key_path = self.script_dir / f"{self.ssh_key_name}.pub"
        if not pub_key_path.exists():
            raise FileNotFoundError(f"Public key not found: {pub_key_path}")

        with open(pub_key_path, 'r') as f:
            public_key = f.read().strip()

        script = f"""#!/bin/bash
set -e

TUNNEL_USER="{config.tunnel_user}"
PROXY_PORT="{config.proxy_port}"
SSH_PUBLIC_KEY="{public_key}"

# Logging functions
log() {{
    echo "[REMOTE-$(date +'%H:%M:%S')] $1"
}}

error() {{
    echo "[REMOTE-ERROR] $1" >&2
    exit 1
}}

# Check if we need sudo or are already root
check_privileges() {{
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
}}

# Function to run commands with appropriate privileges
run_privileged() {{
    if [[ -n "$SUDO_CMD" ]]; then
        $SUDO_CMD "$@"
    else
        "$@"
    fi
}}

# Initialize privilege checking
check_privileges

# Detect OS and package manager
detect_os() {{
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    else
        OS=$(uname -s)
    fi

    log "Detected OS: $OS"
}}

# Install required packages
install_packages() {{
    log "Installing required packages..."

    case "$OS" in
        ubuntu|debian)
            run_privileged apt-get update
            run_privileged apt-get install -y openssh-server curl wget build-essential
            ;;
        centos|rhel|fedora)
            if command -v dnf >/dev/null 2>&1; then
                run_privileged dnf update -y
                run_privileged dnf install -y openssh-server curl wget gcc make
            else
                run_privileged yum update -y
                run_privileged yum install -y openssh-server curl wget gcc make
            fi
            ;;
        *)
            log "Unknown OS, attempting generic installation..."
            ;;
    esac
}}

# Create tunnel user
create_user() {{
    log "Creating tunnel user: $TUNNEL_USER"

    if id "$TUNNEL_USER" &>/dev/null; then
        log "User $TUNNEL_USER already exists"
    else
        run_privileged useradd -m -s /bin/bash "$TUNNEL_USER"
        log "User $TUNNEL_USER created"
    fi

    # Setup SSH directory
    USER_HOME="/home/$TUNNEL_USER"
    SSH_DIR="$USER_HOME/.ssh"

    run_privileged mkdir -p "$SSH_DIR"
    echo "$SSH_PUBLIC_KEY" | run_privileged tee "$SSH_DIR/authorized_keys" > /dev/null
    run_privileged chown -R "$TUNNEL_USER:$TUNNEL_USER" "$SSH_DIR"
    run_privileged chmod 700 "$SSH_DIR"
    run_privileged chmod 600 "$SSH_DIR/authorized_keys"

    log "SSH access configured for $TUNNEL_USER"
}}

# Configure SSH daemon
configure_ssh() {{
    log "Configuring SSH daemon"

    SSH_CONFIG="/etc/ssh/sshd_config"

    # Backup original config
    run_privileged cp "$SSH_CONFIG" "$SSH_CONFIG.backup.$(date +%Y%m%d_%H%M%S)"

    # Configure SSH settings
    run_privileged grep -q "^AllowTcpForwarding" "$SSH_CONFIG" || echo "AllowTcpForwarding yes" | run_privileged tee -a "$SSH_CONFIG" > /dev/null
    run_privileged grep -q "^GatewayPorts" "$SSH_CONFIG" || echo "GatewayPorts no" | run_privileged tee -a "$SSH_CONFIG" > /dev/null
    run_privileged grep -q "^ClientAliveInterval" "$SSH_CONFIG" || echo "ClientAliveInterval 60" | run_privileged tee -a "$SSH_CONFIG" > /dev/null
    run_privileged grep -q "^ClientAliveCountMax" "$SSH_CONFIG" || echo "ClientAliveCountMax 3" | run_privileged tee -a "$SSH_CONFIG" > /dev/null

    # Restart SSH service
    if run_privileged systemctl is-active --quiet sshd; then
        run_privileged systemctl restart sshd
    elif run_privileged systemctl is-active --quiet ssh; then
        run_privileged systemctl restart ssh
    fi

    log "SSH daemon configured and restarted"
}}

# Install and configure SOCKS proxy
setup_proxy() {{
    log "Setting up SOCKS proxy on port $PROXY_PORT"

    # Install dante-server (SOCKS proxy)
    case "$OS" in
        ubuntu|debian)
            run_privileged apt-get install -y dante-server
            ;;
        centos|rhel|fedora)
            if command -v dnf >/dev/null 2>&1; then
                run_privileged dnf install -y dante-server
            else
                run_privileged yum install -y dante-server
            fi
            ;;
    esac

    # Configure dante
    run_privileged tee /etc/danted.conf > /dev/null << EOF
# Dante SOCKS server configuration
logoutput: syslog
user.privileged: root
user.unprivileged: nobody

# Listen on localhost only
internal: 127.0.0.1 port = $PROXY_PORT
external: 127.0.0.1

# Access control
clientmethod: none
socksmethod: none

# Allow access from localhost
client pass {{
    from: 127.0.0.1/32 to: 0.0.0.0/0
    log: error
}}

socks pass {{
    from: 127.0.0.1/32 to: 0.0.0.0/0
    log: error
}}
EOF

    # Create systemd service if not exists
    if [ ! -f /etc/systemd/system/danted.service ]; then
        run_privileged tee /etc/systemd/system/danted.service > /dev/null << EOF
[Unit]
Description=Dante SOCKS proxy
After=network.target

[Service]
Type=forking
PIDFile=/var/run/danted.pid
ExecStart=/usr/sbin/danted -f /etc/danted.conf
ExecReload=/bin/kill -HUP \\\$MAINPID
KillMode=process
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
    fi

    # Start and enable service
    run_privileged systemctl daemon-reload
    run_privileged systemctl enable danted
    run_privileged systemctl restart danted

    if run_privileged systemctl is-active --quiet danted; then
        log "SOCKS proxy started successfully on port $PROXY_PORT"
    else
        log "Warning: SOCKS proxy service may not be running"
    fi
}}

# Configure firewall
configure_firewall() {{
    log "Configuring firewall"

    # UFW (Ubuntu)
    if command -v ufw >/dev/null 2>&1; then
        run_privileged ufw allow ssh
        run_privileged ufw allow from 127.0.0.1 to any port $PROXY_PORT
        echo "y" | run_privileged ufw enable 2>/dev/null || true

    # FirewallD (CentOS/RHEL/Fedora)
    elif command -v firewall-cmd >/dev/null 2>&1; then
        run_privileged firewall-cmd --permanent --add-service=ssh
        run_privileged firewall-cmd --permanent --add-rich-rule="rule family=ipv4 source address=127.0.0.1 port port=$PROXY_PORT protocol=tcp accept"
        run_privileged firewall-cmd --reload

    # iptables fallback
    elif command -v iptables >/dev/null 2>&1; then
        run_privileged iptables -A INPUT -p tcp --dport 22 -j ACCEPT
        run_privileged iptables -A INPUT -s 127.0.0.1 -p tcp --dport $PROXY_PORT -j ACCEPT
        run_privileged iptables -A INPUT -p tcp --dport $PROXY_PORT -j DROP
    fi

    log "Firewall configured"
}}

# Create monitoring script
create_monitoring() {{
    run_privileged tee "/home/$TUNNEL_USER/check_status.sh" > /dev/null << 'MONITOR_EOF'
#!/bin/bash
echo "=== Tunnel Server Status ==="
echo "Date: $(date)"
echo "Hostname: $(hostname)"
echo "User: $(whoami)"
echo ""
echo "Services:"
echo "  SSH: $(systemctl is-active sshd ssh 2>/dev/null | head -1)"
echo "  Proxy: $(systemctl is-active danted 3proxy 2>/dev/null | head -1)"
echo ""
echo "Network:"
echo "  SSH Port 22: $(ss -tlpn | grep ':22 ' | wc -l) listeners"
echo "  Proxy Port: $(ss -tlpn | grep ':PROXY_PORT ' | wc -l) listeners"
echo "  Active connections: $(ss -t | grep -c ESTAB)"
echo ""
echo "System:"
echo "  Load: $(uptime | awk -F'load average:' '{{print $2}}')"
echo "  Memory: $(free -h | grep Mem | awk '{{print $3"/"$2}}')"
echo "  Disk: $(df -h / | tail -1 | awk '{{print $5" used"}}')"
MONITOR_EOF

    run_privileged sed -i "s/PROXY_PORT/$PROXY_PORT/g" "/home/$TUNNEL_USER/check_status.sh"
    run_privileged chmod +x "/home/$TUNNEL_USER/check_status.sh"
    run_privileged chown "$TUNNEL_USER:$TUNNEL_USER" "/home/$TUNNEL_USER/check_status.sh"

    log "Monitoring script created"
}}

# Main execution
main() {{
    log "Starting remote server setup..."

    detect_os
    install_packages
    create_user
    configure_ssh
    setup_proxy
    configure_firewall
    create_monitoring

    log "Remote server setup completed successfully!"
    log "Tunnel user: $TUNNEL_USER"
    log "SOCKS proxy port: $PROXY_PORT"
    log "Status check: /home/$TUNNEL_USER/check_status.sh"
}}

# Execute main function
main
"""
        return script

    def execute_remote_setup(self, config: ServerConfig, dry_run: bool = False) -> SetupResult:
        """Execute setup on a remote server"""
        start_time = time.time()

        logger.info(f"Setting up server: {config.host}")

        if dry_run:
            logger.info(f"[DRY RUN] Would setup {config.host}")
            return SetupResult(
                server=config.host,
                success=True,
                message="Dry run completed",
                execution_time=0.0
            )

        try:
            # Prepare SSH connection
            ssh_opts = [
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'IdentitiesOnly=yes',
                '-p', str(config.ssh_port)
            ]

            if config.ssh_key:
                ssh_opts.extend(['-i', config.ssh_key])

            # Create remote setup script
            remote_script = self.create_remote_setup_script(config)

            # Execute remote script
            ssh_cmd = ['ssh'] + ssh_opts + [f'{config.ssh_user}@{config.host}']

            process = subprocess.Popen(
                ssh_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            stdout, _ = process.communicate(input=remote_script)

            execution_time = time.time() - start_time

            if process.returncode == 0:
                logger.info(f"✅ Server {config.host} setup completed successfully")

                # Test SSH access
                ssh_test = self.test_ssh_access(config)
                proxy_test = self.test_proxy_access(config)

                return SetupResult(
                    server=config.host,
                    success=True,
                    message="Setup completed successfully",
                    execution_time=execution_time,
                    ssh_test_passed=ssh_test,
                    proxy_test_passed=proxy_test
                )
            else:
                logger.error(f"❌ Server {config.host} setup failed")
                logger.error(f"Output: {stdout}")

                return SetupResult(
                    server=config.host,
                    success=False,
                    message=f"Setup failed: {stdout[-500:]}",  # Last 500 chars
                    execution_time=execution_time
                )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Failed to setup {config.host}: {e}")

            return SetupResult(
                server=config.host,
                success=False,
                message=str(e),
                execution_time=execution_time
            )

    def test_ssh_access(self, config: ServerConfig) -> bool:
        """Test SSH access with tunnel user"""
        try:
            ssh_cmd = [
                'ssh',
                '-o', 'ConnectTimeout=10',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'IdentitiesOnly=yes',
                '-p', str(config.ssh_port),
                '-i', str(self.script_dir / self.ssh_key_name),
                f'{config.tunnel_user}@{config.host}',
                'echo "SSH test successful"'
            ]

            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=15
            )

            return result.returncode == 0

        except Exception as e:
            logger.warning(f"SSH test failed for {config.host}: {e}")
            return False

    def test_proxy_access(self, config: ServerConfig) -> bool:
        """Test proxy access through SSH tunnel"""
        try:
            # Create temporary SSH tunnel for testing
            tunnel_cmd = [
                'ssh',
                '-o', 'ConnectTimeout=10',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'IdentitiesOnly=yes',
                '-p', str(config.ssh_port),
                '-i', str(self.script_dir / self.ssh_key_name),
                '-L', f'18080:127.0.0.1:{config.proxy_port}',
                '-N', '-f',
                f'{config.tunnel_user}@{config.host}'
            ]

            # Start tunnel
            tunnel_proc = subprocess.Popen(tunnel_cmd)
            time.sleep(2)  # Wait for tunnel to establish

            # Test SOCKS proxy
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('127.0.0.1', 18080))
            sock.close()

            # Kill tunnel
            tunnel_proc.terminate()
            tunnel_proc.wait()

            return result == 0

        except Exception as e:
            logger.warning(f"Proxy test failed for {config.host}: {e}")
            return False

    def setup_multiple_servers(self, configs: List[ServerConfig], dry_run: bool = False, max_concurrent: int = 5) -> List[SetupResult]:
        """Setup multiple servers concurrently"""
        results = []

        def worker(config: ServerConfig):
            result = self.execute_remote_setup(config, dry_run)
            results.append(result)
            self.results.append(result)

        # Process servers in batches
        for i in range(0, len(configs), max_concurrent):
            batch = configs[i:i + max_concurrent]
            threads = []

            for config in batch:
                thread = threading.Thread(target=worker, args=(config,))
                thread.start()
                threads.append(thread)

            # Wait for batch to complete
            for thread in threads:
                thread.join()

        return results

    def generate_tunnel_config(self, configs: List[ServerConfig]) -> Dict[str, Any]:
        """Generate tunnel configuration file"""
        tunnel_config = {
            "tunnels": {},
            "rotation": {
                "auto_rotate": True,
                "rotation_interval": 1800,
                "random_order": True
            }
        }

        base_port = 8081

        for i, config in enumerate(configs):
            tunnel_config["tunnels"][config.name] = {
                "host": config.host,
                "port": config.ssh_port,
                "username": config.tunnel_user,
                "private_key_path": str(self.script_dir / self.ssh_key_name),
                "local_port": base_port + i,
                "remote_host": "127.0.0.1",
                "remote_port": config.proxy_port,
                "compression": True,
                "keep_alive": 60,
                "max_retries": 3
            }

        # Save configuration
        config_file = self.script_dir / "ssh_tunnels.json"
        with open(config_file, 'w') as f:
            json.dump(tunnel_config, f, indent=2)

        logger.info(f"Tunnel configuration saved: {config_file}")
        return tunnel_config

    def create_management_scripts(self):
        """Create management scripts"""
        scripts = {
            "tunnel_connect.sh": """#!/bin/bash
cd "$(dirname "$0")"
python3 ssh_tunnel_manager.py connect "$1"
""",
            "tunnel_status.sh": """#!/bin/bash
cd "$(dirname "$0")"
python3 ssh_tunnel_manager.py status
""",
            "tunnel_rotate.sh": """#!/bin/bash
cd "$(dirname "$0")"
python3 ssh_tunnel_manager.py rotate
""",
            "servers_health.sh": """#!/bin/bash
cd "$(dirname "$0")"
python3 setup_tunnel_servers.py health-check
"""
        }

        for filename, content in scripts.items():
            script_path = self.script_dir / filename
            with open(script_path, 'w') as f:
                f.write(content)
            os.chmod(script_path, 0o755)

        logger.info(f"Management scripts created in {self.script_dir}")

    def health_check(self, configs: List[ServerConfig]) -> Dict[str, Dict]:
        """Perform health check on configured servers"""
        results = {}

        for config in configs:
            logger.info(f"Health check: {config.host}")

            ssh_ok = self.test_ssh_access(config)
            proxy_ok = self.test_proxy_access(config)

            results[config.host] = {
                "ssh_access": ssh_ok,
                "proxy_access": proxy_ok,
                "status": "healthy" if ssh_ok and proxy_ok else "unhealthy",
                "last_check": datetime.now().isoformat()
            }

            status_icon = "✅" if ssh_ok and proxy_ok else "❌"
            logger.info(f"{status_icon} {config.host}: SSH={ssh_ok}, Proxy={proxy_ok}")

        return results

    def print_summary(self):
        """Print setup summary"""
        if not self.results:
            logger.info("No setup results to display")
            return

        successful = sum(1 for r in self.results if r.success)
        total = len(self.results)

        print(f"\n{'='*60}")
        print(f"SETUP SUMMARY")
        print(f"{'='*60}")
        print(f"Total servers: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {total - successful}")
        print(f"Success rate: {successful/total*100:.1f}%")
        print(f"{'='*60}")

        for result in self.results:
            status = "✅" if result.success else "❌"
            ssh_status = "SSH:✅" if result.ssh_test_passed else "SSH:❌"
            proxy_status = "Proxy:✅" if result.proxy_test_passed else "Proxy:❌"

            print(f"{status} {result.server:<20} {result.execution_time:>6.1f}s {ssh_status} {proxy_status}")
            if not result.success:
                print(f"   Error: {result.message[:80]}")

        print(f"{'='*60}")

def load_servers_from_file(file_path: str) -> List[ServerConfig]:
    """Load server configurations from JSON file"""
    with open(file_path, 'r') as f:
        data = json.load(f)

    servers = []
    for server_data in data.get('servers', []):
        config = ServerConfig(**server_data)
        servers.append(config)

    return servers

def main():
    parser = argparse.ArgumentParser(
        description="Remote Server Setup for SSH Tunneling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Setup single server
  python3 setup_tunnel_servers.py setup 203.0.113.1

  # Setup multiple servers with custom settings
  python3 setup_tunnel_servers.py setup -u admin -k ~/.ssh/admin_key 203.0.113.1 203.0.113.2

  # Setup from configuration file
  python3 setup_tunnel_servers.py setup-from-file servers.json

  # Health check existing servers
  python3 setup_tunnel_servers.py health-check 203.0.113.1 203.0.113.2

  # Dry run
  python3 setup_tunnel_servers.py setup --dry-run 203.0.113.1
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Setup tunnel servers')
    setup_parser.add_argument('servers', nargs='+', help='Server IPs or hostnames')
    setup_parser.add_argument('-u', '--user', default='root', help='SSH username')
    setup_parser.add_argument('-p', '--port', type=int, default=22, help='SSH port')
    setup_parser.add_argument('-k', '--key', help='SSH private key path')
    setup_parser.add_argument('-t', '--tunnel-user', default='tunnel_user', help='Tunnel username')
    setup_parser.add_argument('-P', '--proxy-port', type=int, default=8080, help='Proxy port')
    setup_parser.add_argument('--key-name', default='tunnel_key', help='SSH key name')
    setup_parser.add_argument('--password', action='store_true', help='Use password auth')
    setup_parser.add_argument('--dry-run', action='store_true', help='Dry run')
    setup_parser.add_argument('--max-concurrent', type=int, default=5, help='Max concurrent setups')

    # Setup from file command
    file_parser = subparsers.add_parser('setup-from-file', help='Setup from configuration file')
    file_parser.add_argument('config_file', help='JSON configuration file')
    file_parser.add_argument('--dry-run', action='store_true', help='Dry run')
    file_parser.add_argument('--max-concurrent', type=int, default=5, help='Max concurrent setups')

    # Health check command
    health_parser = subparsers.add_parser('health-check', help='Check server health')
    health_parser.add_argument('servers', nargs='*', help='Server IPs (optional, loads from config if empty)')

    # Generate keys command
    key_parser = subparsers.add_parser('generate-keys', help='Generate SSH keys only')
    key_parser.add_argument('--key-name', default='tunnel_key', help='SSH key name')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = RemoteServerManager()

    if args.command == 'setup':
        # Generate SSH keys
        manager.generate_ssh_keys(getattr(args, 'key_name', 'tunnel_key'))

        # Create server configurations
        configs = []
        for server in args.servers:
            config = ServerConfig(
                host=server,
                ssh_port=args.port,
                ssh_user=args.user,
                ssh_key=args.key,
                use_password=args.password,
                tunnel_user=args.tunnel_user,
                proxy_port=args.proxy_port
            )
            configs.append(config)

        # Setup servers
        results = manager.setup_multiple_servers(configs, args.dry_run, args.max_concurrent)

        # Generate tunnel configuration
        if not args.dry_run:
            manager.generate_tunnel_config(configs)
            manager.create_management_scripts()

        manager.print_summary()

    elif args.command == 'setup-from-file':
        configs = load_servers_from_file(args.config_file)

        # Generate SSH keys
        manager.generate_ssh_keys()

        # Setup servers
        results = manager.setup_multiple_servers(configs, args.dry_run, args.max_concurrent)

        # Generate tunnel configuration
        if not args.dry_run:
            manager.generate_tunnel_config(configs)
            manager.create_management_scripts()

        manager.print_summary()

    elif args.command == 'health-check':
        if args.servers:
            configs = [ServerConfig(host=server) for server in args.servers]
        else:
            # Load from existing configuration
            config_file = manager.script_dir / "ssh_tunnels.json"
            if config_file.exists():
                with open(config_file) as f:
                    tunnel_config = json.load(f)

                configs = []
                for name, tunnel_data in tunnel_config['tunnels'].items():
                    config = ServerConfig(
                        host=tunnel_data['host'],
                        ssh_port=tunnel_data['port'],
                        tunnel_user=tunnel_data['username']
                    )
                    configs.append(config)
            else:
                logger.error("No servers specified and no configuration file found")
                return

        results = manager.health_check(configs)

        # Save results
        health_file = manager.script_dir / "health_check.json"
        with open(health_file, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"Health check results saved: {health_file}")

    elif args.command == 'generate-keys':
        manager.generate_ssh_keys(args.key_name)
        logger.info("SSH keys generated successfully")

if __name__ == '__main__':
    main()