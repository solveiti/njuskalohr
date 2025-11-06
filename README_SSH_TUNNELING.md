# SSH Tunneling System for Web Scraping

A comprehensive SSH tunneling system for distributed web scraping with automatic IP rotation, anti-detection measures, and health monitoring.

## 🚀 Features

- **Automated Server Setup**: Script to establish tunnel users on remote servers
- **SSH Tunnel Management**: Connect, disconnect, rotate, and monitor SSH tunnels
- **SOCKS Proxy Integration**: Automatic proxy configuration for scrapers
- **Health Monitoring**: Real-time tunnel health checks and automatic reconnection
- **Anti-Detection**: Enhanced stealth measures with tunnel rotation
- **Scraper Integration**: Drop-in replacement for existing scrapers with tunnel support

## 📋 Prerequisites

- Python 3.7+
- SSH access to remote servers with key-based authentication
- **sudo privileges on remote servers** (required for system configuration)
- Required Python packages: `subprocess`, `threading`, `socket`, `json`

## 🔧 Installation

1. Clone or download the tunneling system files to your project directory
2. Ensure you have SSH access to your remote servers
3. **Important**: Ensure your SSH user has sudo privileges on remote servers (required for package installation and system configuration)
4. Install any missing dependencies

**Privilege Requirements:**

- Remote servers: SSH user must have sudo access for system configuration
- Local system: Standard user privileges (no sudo required for tunnel management)

## 📁 File Structure

```
├── ssh_tunnel_manager.py          # Core tunnel management system
├── setup_tunnel_servers.py        # Python server setup script
├── setup_tunnel_servers.sh        # Bash server setup script
├── scraper_tunnel_integration.py  # Scraper integration module
├── enhanced_scraper.py            # Enhanced scraper with tunneling
├── servers_config.json            # Sample server configuration
├── ssh_tunnels.json              # Generated tunnel configuration
└── README_SSH_TUNNELING.md       # This file
```

## 🏗️ Setup Process

### Step 1: Configure Your Servers

Edit `servers_config.json` with your remote server details:

```json
{
  "servers": [
    {
      "host": "your-server-1.example.com",
      "ssh_port": 22,
      "ssh_user": "root",
      "tunnel_user": "tunnel_user",
      "proxy_port": 8080,
      "name": "server1"
    },
    {
      "host": "203.0.113.100",
      "ssh_port": 22,
      "ssh_user": "ubuntu",
      "tunnel_user": "scraper_user",
      "proxy_port": 9090,
      "name": "vps1"
    }
  ]
}
```

### Step 2: Setup Remote Servers

#### Option A: Using Python Script (Recommended)

```bash
# Setup servers from configuration file
python3 setup_tunnel_servers.py setup-from-file servers_config.json

# Setup individual servers
python3 setup_tunnel_servers.py setup 203.0.113.1 203.0.113.2

# Setup with custom settings
python3 setup_tunnel_servers.py setup -u admin -t scraper_user -P 9090 203.0.113.1

# Dry run to see what would be executed
python3 setup_tunnel_servers.py setup --dry-run 203.0.113.1
```

#### Option B: Using Bash Script

```bash
# Basic setup
./setup_tunnel_servers.sh 203.0.113.1

# Multiple servers with custom settings
./setup_tunnel_servers.sh -u admin -t scraper_user -P 9090 203.0.113.1 203.0.113.2

# With SSH key authentication
./setup_tunnel_servers.sh -k ~/.ssh/admin_key 203.0.113.1
```

### Step 3: Verify Setup

```bash
# Health check all configured servers
python3 setup_tunnel_servers.py health-check

# Check specific servers
python3 setup_tunnel_servers.py health-check 203.0.113.1 203.0.113.2
```

## 🔗 Tunnel Management

### Basic Tunnel Operations

```bash
# List all configured tunnels
python3 ssh_tunnel_manager.py list

# Connect to a specific tunnel
python3 ssh_tunnel_manager.py connect server1

# Check tunnel status
python3 ssh_tunnel_manager.py status

# Rotate to next available tunnel
python3 ssh_tunnel_manager.py rotate

# Disconnect all tunnels
python3 ssh_tunnel_manager.py disconnect
```

### Using Management Scripts

```bash
# Quick connect
./tunnel_connect.sh server1

# Check status
./tunnel_status.sh

# Rotate tunnels
./tunnel_rotate.sh

# Health check
./servers_health.sh
```

## 🕷️ Scraper Integration

### Using Enhanced Scraper

```bash
# Scrape with automatic tunnel rotation
python3 enhanced_scraper.py --urls urls.txt --auto-rotate

# Single URL with custom delay
python3 enhanced_scraper.py --url 'https://example.com' --delay 20-40

# Custom rotation settings
python3 enhanced_scraper.py --urls urls.txt --auto-rotate --max-requests 50 --rotation-interval 900
```

### Integrating with Existing Scrapers

```python
from scraper_tunnel_integration import TunnelIntegratedScraper

class MyCustomScraper(TunnelIntegratedScraper):
    def __init__(self):
        super().__init__("ssh_tunnels.json")

    def scrape_data(self):
        # Connect to tunnel
        self.connect_tunnel()

        # Get proxy settings for requests
        proxies = self.setup_requests_proxy()

        # Your scraping logic here
        response = requests.get(url, proxies=proxies)

        # Check if rotation is needed
        self.pre_request_hook()
```

### Selenium Integration

```python
from selenium import webdriver
from scraper_tunnel_integration import TunnelIntegratedScraper

scraper = TunnelIntegratedScraper("ssh_tunnels.json")
scraper.connect_tunnel()

# Setup Chrome with proxy
chrome_options = scraper.setup_enhanced_chrome_options()
driver = webdriver.Chrome(options=chrome_options)
```

## ⚙️ Configuration

### SSH Tunnel Configuration (`ssh_tunnels.json`)

```json
{
  "tunnels": {
    "server1": {
      "host": "203.0.113.1",
      "port": 22,
      "username": "tunnel_user",
      "private_key_path": "./tunnel_key",
      "local_port": 8081,
      "remote_host": "127.0.0.1",
      "remote_port": 8080,
      "compression": true,
      "keep_alive": 60,
      "max_retries": 3
    }
  },
  "rotation": {
    "auto_rotate": true,
    "rotation_interval": 1800,
    "random_order": true
  }
}
```

### Environment Variables

```bash
export SSH_TUNNEL_CONFIG="./ssh_tunnels.json"
export TUNNEL_AUTO_ROTATE="true"
export TUNNEL_ROTATION_INTERVAL="1800"
export TUNNEL_MAX_RETRIES="3"
```

## 🔍 Monitoring and Debugging

### Health Monitoring

```bash
# Continuous health monitoring
python3 ssh_tunnel_manager.py monitor

# Check tunnel logs
python3 ssh_tunnel_manager.py logs server1

# Debug connection issues
python3 ssh_tunnel_manager.py debug server1
```

### Log Files

- `tunnel_manager.log` - Tunnel management operations
- `server_setup.log` - Server setup operations
- `health_check.json` - Latest health check results

### Common Issues and Solutions

#### Connection Refused

````bash
# Check if SSH service is running on remote server
ssh user@server "systemctl status sshd"

#### Setup Requirements

Before running the setup scripts, ensure your target servers have:

1. SSH access enabled and configured
2. A user account with **either**:
   - Root access (user `root`)
   - Regular user with **passwordless sudo** privileges
3. Standard package managers (apt/yum/dnf) available

#### Privilege Configuration

The setup scripts automatically detect your privilege level and adapt accordingly. You have three options:

**Option 1: Root User (Recommended)**
```bash
# Connect directly as root
ssh root@your-server
````

**Option 2: Passwordless Sudo User**

```bash
# Configure passwordless sudo on the remote server
ssh user@server
sudo visudo
# Add this line (replace 'username' with actual username):
username ALL=(ALL) NOPASSWD:ALL

# Or use sudoers.d (safer approach):
echo "username ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/username
sudo chmod 440 /etc/sudoers.d/username
```

**Option 3: Regular User with Sudo (Not Recommended for Automation)**
If your user requires a password for sudo, the scripts will fail during remote execution since SSH cannot prompt for passwords interactively.

#### Testing Your Configuration

Verify your setup before running the scripts:

```bash
# Test privilege level detection
ssh user@server "whoami; sudo -n whoami 2>/dev/null || echo 'No passwordless sudo'"

# Test package management access
ssh user@server "sudo -n apt-get update" || echo "Cannot install packages"
```

#### Permission Denied Errors

If you encounter permission denied errors like:

```
sudo: a terminal is required to read the password
E: Could not open lock file /var/lib/apt/lists/lock - open (13: Permission denied)
```

**Solution:**
Your user needs passwordless sudo access. Follow the "Passwordless Sudo User" configuration above.

#### Connection Refused

```bash
# Check if SSH service is running on remote server
ssh user@server "systemctl status sshd"

# Verify firewall settings
ssh user@server "ufw status"
```

#### Proxy Not Working

```bash
# Test proxy connection
curl --socks5 127.0.0.1:8081 http://httpbin.org/ip

# Check proxy service on remote server
ssh tunnel_user@server "./check_status.sh"
```

#### SSH Key Issues

```bash
# Regenerate SSH keys
python3 setup_tunnel_servers.py generate-keys --key-name new_tunnel_key

# Test SSH access
ssh -i tunnel_key tunnel_user@server "echo 'Connection test'"
```

## 🚀 Advanced Usage

### Custom Rotation Strategies

```python
from ssh_tunnel_manager import SSHTunnelManager

manager = SSHTunnelManager("ssh_tunnels.json")

# Geographic rotation (if servers are in different regions)
def rotate_by_region():
    us_tunnels = [name for name in manager.list_tunnels() if 'us' in name]
    eu_tunnels = [name for name in manager.list_tunnels() if 'eu' in name]
    # Implement custom rotation logic

# Performance-based rotation
def rotate_by_latency():
    # Test latency for each tunnel and select best performing
    pass
```

### Bulk Server Management

```python
# Setup 10 servers concurrently
servers = [f"server-{i}.example.com" for i in range(1, 11)]
configs = [ServerConfig(host=server) for server in servers]

manager = RemoteServerManager()
results = manager.setup_multiple_servers(configs, max_concurrent=5)
```

### Integration with Existing Anti-Detection

```python
class StealthScraper(TunnelIntegratedScraper):
    def __init__(self):
        super().__init__()

        # Combine tunnel rotation with other anti-detection
        self.user_agents = [...]
        self.browser_profiles = [...]

    def enhanced_stealth_request(self, url):
        # Rotate tunnel
        self.pre_request_hook()

        # Apply additional stealth measures
        headers = self.get_random_headers()
        proxies = self.setup_requests_proxy()

        # Make request with full stealth stack
        return requests.get(url, headers=headers, proxies=proxies)
```

## 📊 Performance Optimization

### Tunnel Pool Management

- **Connection Pooling**: Maintain multiple active tunnels
- **Load Balancing**: Distribute requests across tunnels
- **Geographic Distribution**: Use servers in different regions
- **Health-Based Selection**: Prefer healthy, fast tunnels

### Recommended Settings

- **Rotation Interval**: 15-30 minutes for aggressive rotation
- **Requests per Tunnel**: 50-100 requests before rotation
- **Concurrent Tunnels**: 3-5 active tunnels for load distribution
- **Health Check Interval**: 5 minutes for proactive monitoring

## 🔐 Security Considerations

- **SSH Key Management**: Use dedicated keys for tunnel access
- **User Isolation**: Create separate tunnel users with minimal privileges
- **Firewall Rules**: Restrict proxy access to localhost only
- **Connection Encryption**: All traffic encrypted through SSH tunnels
- **Audit Logging**: Monitor tunnel usage and access patterns

## 🤝 Contributing

To extend the tunneling system:

1. Follow the modular design pattern
2. Add comprehensive error handling
3. Include logging for debugging
4. Write tests for new functionality
5. Update documentation

## 📝 License

This SSH tunneling system is provided as-is for educational and legitimate scraping purposes. Ensure compliance with target website terms of service and applicable laws.

---

## Quick Start Checklist

- [ ] Configure server details in `servers_config.json`
- [ ] Run server setup: `python3 setup_tunnel_servers.py setup-from-file servers_config.json`
- [ ] Verify health: `python3 setup_tunnel_servers.py health-check`
- [ ] Test tunnel: `python3 ssh_tunnel_manager.py connect server1`
- [ ] Run enhanced scraper: `python3 enhanced_scraper.py --urls urls.txt --auto-rotate`
- [ ] Monitor performance: `python3 ssh_tunnel_manager.py status`

For support or issues, check the log files and use the debug commands provided.
