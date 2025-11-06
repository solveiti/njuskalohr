#!/usr/bin/env python3
"""
SSH Tunnel Manager for IP rotation and remote proxy connections.

This module provides functionality to:
1. Establish SSH tunnels through remote servers
2. Rotate IP addresses for scraping
3. Manage multiple tunnel connections
4. Monitor tunnel health and auto-reconnect
"""

import subprocess
import time
import random
import json
import logging
import threading
import socket
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class SSHTunnelConfig:
    """Configuration for an SSH tunnel connection."""
    name: str
    host: str
    port: int
    username: str
    private_key_path: str
    local_port: int
    remote_host: str = "127.0.0.1"
    remote_port: int = 8080
    compression: bool = True
    keep_alive: int = 60
    max_retries: int = 3


class SSHTunnelManager:
    """Manages SSH tunnels for IP rotation and proxy connections."""

    def __init__(self, config_file: str = "ssh_tunnels.json"):
        """
        Initialize SSH tunnel manager.

        Args:
            config_file: Path to JSON configuration file
        """
        self.config_file = config_file
        self.tunnels: Dict[str, SSHTunnelConfig] = {}
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.health_threads: Dict[str, threading.Thread] = {}
        self.is_monitoring = False
        self.current_tunnel: Optional[str] = None

        self.load_configuration()

    def load_configuration(self) -> None:
        """Load tunnel configurations from file."""
        config_path = Path(self.config_file)

        if not config_path.exists():
            logger.warning(f"Configuration file {self.config_file} not found. Creating example.")
            self.create_example_config()
            return

        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)

            for name, config in config_data.get('tunnels', {}).items():
                self.tunnels[name] = SSHTunnelConfig(
                    name=name,
                    host=config['host'],
                    port=config.get('port', 22),
                    username=config['username'],
                    private_key_path=config['private_key_path'],
                    local_port=config['local_port'],
                    remote_host=config.get('remote_host', '127.0.0.1'),
                    remote_port=config.get('remote_port', 8080),
                    compression=config.get('compression', True),
                    keep_alive=config.get('keep_alive', 60),
                    max_retries=config.get('max_retries', 3)
                )

            logger.info(f"Loaded {len(self.tunnels)} tunnel configurations")

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            self.create_example_config()

    def create_example_config(self) -> None:
        """Create an example configuration file."""
        example_config = {
            "tunnels": {
                "server1": {
                    "host": "your-server1.com",
                    "port": 22,
                    "username": "tunnel_user",
                    "private_key_path": "~/.ssh/tunnel_key",
                    "local_port": 8081,
                    "remote_host": "127.0.0.1",
                    "remote_port": 8080,
                    "compression": True,
                    "keep_alive": 60,
                    "max_retries": 3
                },
                "server2": {
                    "host": "your-server2.com",
                    "port": 22,
                    "username": "tunnel_user",
                    "private_key_path": "~/.ssh/tunnel_key",
                    "local_port": 8082,
                    "remote_host": "127.0.0.1",
                    "remote_port": 8080,
                    "compression": True,
                    "keep_alive": 60,
                    "max_retries": 3
                }
            },
            "rotation": {
                "auto_rotate": True,
                "rotation_interval": 1800,
                "random_order": True
            }
        }

        with open(self.config_file, 'w') as f:
            json.dump(example_config, f, indent=2)

        logger.info(f"Created example configuration at {self.config_file}")
        logger.info("Please edit the configuration file with your server details")

    def establish_tunnel(self, tunnel_name: str) -> bool:
        """
        Establish an SSH tunnel.

        Args:
            tunnel_name: Name of the tunnel configuration

        Returns:
            True if tunnel established successfully
        """
        if tunnel_name not in self.tunnels:
            logger.error(f"Tunnel configuration '{tunnel_name}' not found")
            return False

        config = self.tunnels[tunnel_name]

        # Check if tunnel is already active
        if tunnel_name in self.active_processes:
            if self.is_tunnel_healthy(tunnel_name):
                logger.info(f"Tunnel '{tunnel_name}' is already active")
                return True
            else:
                self.close_tunnel(tunnel_name)

        # Build SSH command
        ssh_cmd = self._build_ssh_command(config)

        try:
            logger.info(f"Establishing tunnel '{tunnel_name}' to {config.host}:{config.port}")

            # Start SSH process
            process = subprocess.Popen(
                ssh_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE
            )

            # Wait a moment for connection to establish
            time.sleep(2)

            # Check if process is still running
            if process.poll() is None:
                self.active_processes[tunnel_name] = process
                self.current_tunnel = tunnel_name

                # Start health monitoring
                self._start_health_monitoring(tunnel_name)

                logger.info(f"Tunnel '{tunnel_name}' established successfully on local port {config.local_port}")
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(f"Failed to establish tunnel '{tunnel_name}': {stderr.decode()}")
                return False

        except Exception as e:
            logger.error(f"Error establishing tunnel '{tunnel_name}': {e}")
            return False

    def _build_ssh_command(self, config: SSHTunnelConfig) -> List[str]:
        """Build SSH command for tunnel."""
        cmd = [
            'ssh',
            '-N',  # No remote command
            '-T',  # Disable pseudo-terminal allocation
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'IdentitiesOnly=yes',
            '-o', f'ServerAliveInterval={config.keep_alive}',
            '-o', 'ServerAliveCountMax=3',
            '-o', 'ExitOnForwardFailure=yes',
            '-L', f'{config.local_port}:{config.remote_host}:{config.remote_port}',
            '-p', str(config.port),
            '-i', os.path.expanduser(config.private_key_path),
        ]

        if config.compression:
            cmd.append('-C')

        cmd.append(f'{config.username}@{config.host}')

        return cmd

    def close_tunnel(self, tunnel_name: str) -> bool:
        """
        Close an SSH tunnel.

        Args:
            tunnel_name: Name of the tunnel to close

        Returns:
            True if tunnel closed successfully
        """
        if tunnel_name not in self.active_processes:
            logger.warning(f"Tunnel '{tunnel_name}' is not active")
            return True

        try:
            process = self.active_processes[tunnel_name]
            process.terminate()

            # Wait for graceful termination
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing tunnel '{tunnel_name}'")
                process.kill()
                process.wait()

            del self.active_processes[tunnel_name]

            # Stop health monitoring
            if tunnel_name in self.health_threads:
                del self.health_threads[tunnel_name]

            if self.current_tunnel == tunnel_name:
                self.current_tunnel = None

            logger.info(f"Tunnel '{tunnel_name}' closed successfully")
            return True

        except Exception as e:
            logger.error(f"Error closing tunnel '{tunnel_name}': {e}")
            return False

    def rotate_tunnel(self, exclude_current: bool = True) -> Optional[str]:
        """
        Rotate to a different tunnel.

        Args:
            exclude_current: Whether to exclude the current tunnel from rotation

        Returns:
            Name of the new tunnel or None if rotation failed
        """
        available_tunnels = list(self.tunnels.keys())

        if exclude_current and self.current_tunnel:
            available_tunnels = [t for t in available_tunnels if t != self.current_tunnel]

        if not available_tunnels:
            logger.warning("No tunnels available for rotation")
            return None

        # Close current tunnel
        if self.current_tunnel:
            self.close_tunnel(self.current_tunnel)

        # Select random tunnel
        new_tunnel = random.choice(available_tunnels)

        if self.establish_tunnel(new_tunnel):
            logger.info(f"Successfully rotated to tunnel '{new_tunnel}'")
            return new_tunnel
        else:
            logger.error(f"Failed to rotate to tunnel '{new_tunnel}'")
            return None

    def is_tunnel_healthy(self, tunnel_name: str) -> bool:
        """
        Check if a tunnel is healthy.

        Args:
            tunnel_name: Name of the tunnel to check

        Returns:
            True if tunnel is healthy
        """
        if tunnel_name not in self.active_processes:
            return False

        process = self.active_processes[tunnel_name]

        # Check if process is still running
        if process.poll() is not None:
            return False

        # Test local port connectivity
        config = self.tunnels[tunnel_name]
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('127.0.0.1', config.local_port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _start_health_monitoring(self, tunnel_name: str) -> None:
        """Start health monitoring for a tunnel."""
        def monitor():
            while tunnel_name in self.active_processes:
                time.sleep(30)  # Check every 30 seconds

                if not self.is_tunnel_healthy(tunnel_name):
                    logger.warning(f"Tunnel '{tunnel_name}' became unhealthy, attempting reconnection")

                    # Try to re-establish
                    config = self.tunnels[tunnel_name]
                    for attempt in range(config.max_retries):
                        if tunnel_name in self.active_processes:
                            self.close_tunnel(tunnel_name)

                        time.sleep(5)  # Wait before retry

                        if self.establish_tunnel(tunnel_name):
                            logger.info(f"Successfully reconnected tunnel '{tunnel_name}'")
                            break
                        else:
                            logger.warning(f"Reconnection attempt {attempt + 1} failed for '{tunnel_name}'")
                    else:
                        logger.error(f"Failed to reconnect tunnel '{tunnel_name}' after {config.max_retries} attempts")
                        break

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        self.health_threads[tunnel_name] = thread

    def get_proxy_settings(self, tunnel_name: Optional[str] = None) -> Optional[Dict[str, str]]:
        """
        Get proxy settings for the current or specified tunnel.

        Args:
            tunnel_name: Name of tunnel, or None for current tunnel

        Returns:
            Dictionary with proxy settings or None
        """
        tunnel = tunnel_name or self.current_tunnel

        if not tunnel or tunnel not in self.tunnels:
            return None

        config = self.tunnels[tunnel]

        return {
            'http': f'socks5://127.0.0.1:{config.local_port}',
            'https': f'socks5://127.0.0.1:{config.local_port}',
            'local_port': config.local_port,
            'tunnel_name': tunnel
        }

    def list_tunnels(self) -> Dict[str, Dict[str, any]]:
        """List all configured tunnels and their status."""
        result = {}

        for name, config in self.tunnels.items():
            result[name] = {
                'config': {
                    'host': config.host,
                    'port': config.port,
                    'username': config.username,
                    'local_port': config.local_port
                },
                'active': name in self.active_processes,
                'healthy': self.is_tunnel_healthy(name),
                'current': name == self.current_tunnel
            }

        return result

    def close_all_tunnels(self) -> None:
        """Close all active tunnels."""
        tunnel_names = list(self.active_processes.keys())

        for tunnel_name in tunnel_names:
            self.close_tunnel(tunnel_name)

        logger.info("All tunnels closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_all_tunnels()


# CLI interface functions
def main():
    """Main CLI interface for tunnel management."""
    import argparse

    parser = argparse.ArgumentParser(description='SSH Tunnel Manager')
    parser.add_argument('--config', default='ssh_tunnels.json', help='Configuration file path')

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # List command
    subparsers.add_parser('list', help='List all tunnels')

    # Connect command
    connect_parser = subparsers.add_parser('connect', help='Connect to a tunnel')
    connect_parser.add_argument('tunnel_name', help='Name of the tunnel to connect')

    # Disconnect command
    disconnect_parser = subparsers.add_parser('disconnect', help='Disconnect from a tunnel')
    disconnect_parser.add_argument('tunnel_name', help='Name of the tunnel to disconnect')

    # Rotate command
    subparsers.add_parser('rotate', help='Rotate to a different tunnel')

    # Status command
    subparsers.add_parser('status', help='Show current tunnel status')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = SSHTunnelManager(args.config)

    try:
        if args.command == 'list':
            tunnels = manager.list_tunnels()
            print("\n🌐 Available SSH Tunnels:")
            print("=" * 50)

            for name, info in tunnels.items():
                status = "🟢 Active" if info['active'] else "🔴 Inactive"
                health = "✅ Healthy" if info['healthy'] else "❌ Unhealthy"
                current = "⭐ Current" if info['current'] else ""

                print(f"\n📡 {name} {current}")
                print(f"   Host: {info['config']['host']}:{info['config']['port']}")
                print(f"   User: {info['config']['username']}")
                print(f"   Local Port: {info['config']['local_port']}")
                print(f"   Status: {status}")
                if info['active']:
                    print(f"   Health: {health}")

        elif args.command == 'connect':
            if manager.establish_tunnel(args.tunnel_name):
                print(f"✅ Connected to tunnel '{args.tunnel_name}'")
                proxy = manager.get_proxy_settings()
                if proxy:
                    print(f"📡 Proxy: {proxy['http']}")
            else:
                print(f"❌ Failed to connect to tunnel '{args.tunnel_name}'")

        elif args.command == 'disconnect':
            if manager.close_tunnel(args.tunnel_name):
                print(f"✅ Disconnected from tunnel '{args.tunnel_name}'")
            else:
                print(f"❌ Failed to disconnect from tunnel '{args.tunnel_name}'")

        elif args.command == 'rotate':
            new_tunnel = manager.rotate_tunnel()
            if new_tunnel:
                print(f"✅ Rotated to tunnel '{new_tunnel}'")
                proxy = manager.get_proxy_settings()
                if proxy:
                    print(f"📡 Proxy: {proxy['http']}")
            else:
                print("❌ Failed to rotate tunnel")

        elif args.command == 'status':
            if manager.current_tunnel:
                print(f"📡 Current tunnel: {manager.current_tunnel}")
                proxy = manager.get_proxy_settings()
                if proxy:
                    print(f"🔗 Proxy: {proxy['http']}")
                    print(f"🏥 Health: {'✅ Healthy' if manager.is_tunnel_healthy(manager.current_tunnel) else '❌ Unhealthy'}")
            else:
                print("🔴 No active tunnel")

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        manager.close_all_tunnels()


if __name__ == "__main__":
    main()