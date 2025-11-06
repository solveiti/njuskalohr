#!/bin/bash
# Tunnel rotation script
cd "$(dirname "$0")"
python3 ssh_tunnel_manager.py rotate
