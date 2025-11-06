# 🚀 Next Steps: Integrating 3proxy with Your Scraper

After successfully setting up 3proxy on your server, here's how to integrate it with your scraping system:

## 📋 **Step-by-Step Integration Guide**

### **Step 1: Generate SSH Keys for Tunnel Access**

First, generate SSH keys that the scraper will use to connect to your tunnel server:

```bash
# Generate SSH key pair for tunnel connections
ssh-keygen -t rsa -b 4096 -f ~/.ssh/tunnel_key -N '' -C "scraper-tunnel-$(date +%Y%m%d)"

# Display the public key (you'll need this for the next step)
cat ~/.ssh/tunnel_key.pub
```

### **Step 2: Add Public Key to Server**

Copy the public key content and add it to your server:

```bash
# On your server (where 3proxy is running), run as root:
sudo su - tunnel_user

# Create .ssh directory if it doesn't exist
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Add your public key to authorized_keys
echo "YOUR_PUBLIC_KEY_CONTENT_HERE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### **Step 3: Configure SSH Tunnel Manager**

Update your SSH tunnel configuration to include your new server:

```python
# In ssh_tunnel_manager.py or create a new config file
tunnel_configs = [
    {
        "name": "server1",
        "host": "YOUR_SERVER_IP",  # Replace with your server's IP
        "port": 22,
        "username": "tunnel_user",
        "private_key_path": "/home/srdjan/.ssh/tunnel_key",
        "local_port": 8081,  # Local SOCKS proxy port
        "remote_host": "127.0.0.1",
        "remote_port": 8080,  # 3proxy port on remote server
    }
]
```

### **Step 4: Test SSH Tunnel Connection**

Test the tunnel connection manually first:

```bash
# Test SSH connection
ssh -i ~/.ssh/tunnel_key tunnel_user@YOUR_SERVER_IP "echo 'SSH connection successful'"

# Test SSH tunnel (run in background)
ssh -D 8081 -f -C -q -N -o IdentitiesOnly=yes -i ~/.ssh/tunnel_key tunnel_user@YOUR_SERVER_IP

# Test SOCKS proxy
curl --socks5 127.0.0.1:8081 http://httpbin.org/ip

# Kill the tunnel when done testing
pkill -f "ssh -D 8081"
```

### **Step 5: Update Your Scraper Configuration**

Now integrate the tunnel with your existing scraper. Here's how to modify your scraper:

#### **Option A: Update Existing Scraper**

```python
# Add this to your scraper imports
from ssh_tunnel_manager import SSHTunnelManager

# Initialize tunnel manager
tunnel_manager = SSHTunnelManager()

# Add your server configuration
tunnel_manager.add_tunnel(
    name="server1",
    host="YOUR_SERVER_IP",
    port=22,
    username="tunnel_user",
    private_key_path="/home/srdjan/.ssh/tunnel_key",
    local_port=8081,
    remote_port=8080
)

# Start the tunnel
tunnel_manager.start_tunnel("server1")

# Configure your Chrome driver to use the SOCKS proxy
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_argument("--proxy-server=socks5://127.0.0.1:8081")

# Use this in your scraper
driver = webdriver.Chrome(options=chrome_options)
```

#### **Option B: Use the Enhanced Scraper**

If you have the enhanced scraper with tunnel integration:

```python
# Update your scraper configuration
TUNNEL_CONFIG = {
    "servers": [
        {
            "name": "server1",
            "host": "YOUR_SERVER_IP",
            "username": "tunnel_user",
            "key_path": "/home/srdjan/.ssh/tunnel_key"
        }
    ],
    "rotation_enabled": True,
    "tunnel_timeout": 30
}

# Run with tunnel rotation
python enhanced_scraper.py --use-tunnels --rotate-ip
```

### **Step 6: Verify Everything Works**

Create a simple test script to verify the integration:

```python
#!/usr/bin/env python3
"""Test script to verify 3proxy + SSH tunnel integration"""

import requests
import time
from ssh_tunnel_manager import SSHTunnelManager

def test_tunnel_integration():
    # Initialize tunnel manager
    tunnel_manager = SSHTunnelManager()

    # Add your server
    tunnel_manager.add_tunnel(
        name="test_server",
        host="YOUR_SERVER_IP",  # Replace with actual IP
        port=22,
        username="tunnel_user",
        private_key_path="/home/srdjan/.ssh/tunnel_key",
        local_port=8081,
        remote_port=8080
    )

    try:
        # Start tunnel
        print("Starting SSH tunnel...")
        tunnel_manager.start_tunnel("test_server")
        time.sleep(3)  # Wait for tunnel to establish

        # Test proxy connection
        print("Testing proxy connection...")
        proxies = {
            'http': 'socks5://127.0.0.1:8081',
            'https': 'socks5://127.0.0.1:8081'
        }

        # Check IP without proxy
        response = requests.get('http://httpbin.org/ip', timeout=10)
        original_ip = response.json()['origin']
        print(f"Original IP: {original_ip}")

        # Check IP with proxy
        response = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=10)
        proxy_ip = response.json()['origin']
        print(f"Proxy IP: {proxy_ip}")

        if original_ip != proxy_ip:
            print("✅ SUCCESS: IP rotation working!")
            return True
        else:
            print("❌ FAILED: IP not changed")
            return False

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    finally:
        # Clean up
        tunnel_manager.stop_tunnel("test_server")
        print("Tunnel stopped")

if __name__ == "__main__":
    test_tunnel_integration()
```

### **Step 7: Production Usage**

For production scraping, you can now:

1. **Use Multiple Servers**: Add more servers to `tunnel_configs` for better IP rotation
2. **Implement Health Monitoring**: The tunnel manager includes health checks
3. **Auto-Reconnection**: Tunnels will automatically reconnect if they fail
4. **Load Balancing**: Rotate between different tunnel servers

### **Step 8: Monitor and Maintain**

Set up monitoring for your tunnel servers:

```bash
# Check server status
ssh tunnel_user@YOUR_SERVER_IP "./check_status.sh"

# Check 3proxy service
ssh tunnel_user@YOUR_SERVER_IP "systemctl status 3proxy"

# View 3proxy logs
ssh tunnel_user@YOUR_SERVER_IP "sudo journalctl -fu 3proxy"
```

## 🔧 **Quick Commands Reference**

```bash
# Start manual tunnel (for testing)
ssh -D 8081 -f -C -q -N -o IdentitiesOnly=yes -i ~/.ssh/tunnel_key tunnel_user@YOUR_SERVER_IP

# Test proxy
curl --socks5 127.0.0.1:8081 http://httpbin.org/ip

# Kill tunnel
pkill -f "ssh -D 8081"

# Check server status
ssh tunnel_user@YOUR_SERVER_IP "./check_status.sh"
```

## 🚨 **Important Notes**

1. **Replace `YOUR_SERVER_IP`** with your actual server IP address
2. **Update key paths** to match your local setup
3. **Test thoroughly** before production use
4. **Monitor tunnel health** regularly
5. **Keep SSH keys secure** - never commit them to version control

## 🎯 **Expected Results**

After completing these steps:

- ✅ Your scraper will route traffic through the remote server
- ✅ Your IP address will appear as the server's IP
- ✅ 3proxy will handle SOCKS connections locally on the server
- ✅ SSH tunnel will securely forward connections
- ✅ You'll have rotating IP capability with multiple servers

The integration is now complete and ready for production scraping!
