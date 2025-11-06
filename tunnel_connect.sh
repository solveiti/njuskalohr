#!/bin/bash
# Quick tunnel connection script
cd "$(dirname "$0")"
python3 ssh_tunnel_manager.py connect "$1"
