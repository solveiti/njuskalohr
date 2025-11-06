#!/bin/bash
cd "$(dirname "$0")"
python3 setup_tunnel_servers.py health-check
