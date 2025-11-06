#!/usr/bin/env python3
"""
Quick Integration Test for 3proxy + SSH Tunnel Setup

This script tests the complete integration between your local scraper
and the remote 3proxy server through SSH tunnels.
"""

import requests
import subprocess
import time
import sys
import os
from typing import Optional

def run_command(cmd: str, timeout: int = 30) -> tuple[bool, str]:
    """Run a shell command and return success status and output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout} seconds"
    except Exception as e:
        return False, str(e)

def check_ssh_connection(server_ip: str, username: str = "tunnel_user", key_path: str = "~/.ssh/tunnel_key") -> bool:
    """Test SSH connection to the server."""
    print(f"🔍 Testing SSH connection to {username}@{server_ip}...")

    cmd = f'ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no -i {key_path} {username}@{server_ip} "echo \'SSH OK\'"'
    success, output = run_command(cmd)

    if success and "SSH OK" in output:
        print("✅ SSH connection successful")
        return True
    else:
        print(f"❌ SSH connection failed: {output}")
        return False

def start_ssh_tunnel(server_ip: str, local_port: int = 8081, username: str = "tunnel_user", key_path: str = "~/.ssh/tunnel_key") -> bool:
    """Start SSH tunnel in background."""
    print(f"🚇 Starting SSH tunnel on port {local_port}...")

    # Kill any existing tunnel on this port
    run_command(f"pkill -f 'ssh -D {local_port}'")
    time.sleep(2)

    # Start new tunnel
    cmd = f'ssh -D {local_port} -f -C -q -N -o IdentitiesOnly=yes -o StrictHostKeyChecking=no -i {key_path} {username}@{server_ip}'
    success, output = run_command(cmd)

    if success:
        # Wait a moment for tunnel to establish
        time.sleep(3)
        print("✅ SSH tunnel started")
        return True
    else:
        print(f"❌ Failed to start SSH tunnel: {output}")
        return False

def test_proxy_connection(local_port: int = 8081) -> bool:
    """Test SOCKS proxy connection."""
    print(f"🌐 Testing SOCKS proxy on port {local_port}...")

    proxies = {
        'http': f'socks5://127.0.0.1:{local_port}',
        'https': f'socks5://127.0.0.1:{local_port}'
    }

    try:
        # Test with httpbin.org
        response = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=15)
        if response.status_code == 200:
            ip_data = response.json()
            proxy_ip = ip_data['origin']
            print(f"✅ Proxy working! Remote IP: {proxy_ip}")
            return True
        else:
            print(f"❌ Proxy test failed with status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Proxy test failed: {e}")
        return False

def get_original_ip() -> Optional[str]:
    """Get the original IP address (without proxy)."""
    try:
        response = requests.get('http://httpbin.org/ip', timeout=10)
        if response.status_code == 200:
            return response.json()['origin']
    except Exception as e:
        print(f"Warning: Could not get original IP: {e}")
    return None

def stop_ssh_tunnel(local_port: int = 8081):
    """Stop SSH tunnel."""
    print(f"🛑 Stopping SSH tunnel on port {local_port}...")
    success, output = run_command(f"pkill -f 'ssh -D {local_port}'")
    if success:
        print("✅ SSH tunnel stopped")
    else:
        print(f"⚠️ Could not stop tunnel (might not be running): {output}")

def check_server_status(server_ip: str, username: str = "tunnel_user", key_path: str = "~/.ssh/tunnel_key"):
    """Check remote server status."""
    print(f"📊 Checking server status...")

    cmd = f'ssh -o ConnectTimeout=10 -i {key_path} {username}@{server_ip} "./check_status.sh"'
    success, output = run_command(cmd)

    if success:
        print("✅ Server status:")
        print(output)
    else:
        print(f"❌ Could not get server status: {output}")

def main():
    """Main test function."""
    print("🔧 3proxy + SSH Tunnel Integration Test")
    print("=" * 50)

    # Configuration - UPDATE THESE VALUES
    SERVER_IP = input("Enter your server IP address: ").strip()
    if not SERVER_IP:
        print("❌ Server IP is required")
        sys.exit(1)

    USERNAME = "tunnel_user"
    KEY_PATH = "~/.ssh/tunnel_key"
    LOCAL_PORT = 8081

    print(f"\nConfiguration:")
    print(f"  Server: {USERNAME}@{SERVER_IP}")
    print(f"  SSH Key: {KEY_PATH}")
    print(f"  Local Port: {LOCAL_PORT}")
    print()

    # Expand tilde in key path
    key_path_expanded = os.path.expanduser(KEY_PATH)
    if not os.path.exists(key_path_expanded):
        print(f"❌ SSH key not found: {key_path_expanded}")
        print("   Generate it with: ssh-keygen -t rsa -b 4096 -f ~/.ssh/tunnel_key")
        sys.exit(1)

    # Get original IP
    original_ip = get_original_ip()
    if original_ip:
        print(f"🏠 Your original IP: {original_ip}")
    print()

    try:
        # Test 1: SSH Connection
        if not check_ssh_connection(SERVER_IP, USERNAME, KEY_PATH):
            print("\n❌ SSH connection failed. Check:")
            print("   1. Server IP is correct")
            print("   2. SSH key is properly configured")
            print("   3. tunnel_user exists on server")
            print("   4. Public key is in ~/.ssh/authorized_keys")
            sys.exit(1)

        print()

        # Test 2: Check server status
        check_server_status(SERVER_IP, USERNAME, KEY_PATH)
        print()

        # Test 3: Start SSH tunnel
        if not start_ssh_tunnel(SERVER_IP, LOCAL_PORT, USERNAME, KEY_PATH):
            print("❌ Could not start SSH tunnel")
            sys.exit(1)

        print()

        # Test 4: Test proxy
        if not test_proxy_connection(LOCAL_PORT):
            print("❌ Proxy test failed")
            sys.exit(1)

        print()
        print("🎉 SUCCESS! Integration test completed successfully!")
        print("\nNext steps:")
        print("1. Update your scraper to use SOCKS proxy: socks5://127.0.0.1:8081")
        print("2. Add this server configuration to your tunnel manager")
        print("3. Test with your actual scraper code")

    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        stop_ssh_tunnel(LOCAL_PORT)
        print("✅ Cleanup completed")

if __name__ == "__main__":
    main()