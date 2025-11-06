#!/bin/bash
"""
Test Script for SSH Tunnel Setup

This script performs basic validation of the tunnel setup scripts
and provides debugging information for common issues.
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[TEST]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[TEST]${NC} $1"
}

error() {
    echo -e "${RED}[TEST]${NC} $1"
}

info() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

# Test if required scripts exist
test_script_files() {
    log "Testing script files..."

    local files=(
        "setup_tunnel_servers.sh"
        "setup_tunnel_servers.py"
        "ssh_tunnel_manager.py"
        "scraper_tunnel_integration.py"
        "servers_config.json"
    )

    for file in "${files[@]}"; do
        if [[ -f "$file" ]]; then
            info "✅ $file exists"
        else
            error "❌ $file missing"
        fi
    done
}

# Test if scripts have proper permissions
test_permissions() {
    log "Testing script permissions..."

    local scripts=(
        "setup_tunnel_servers.sh"
        "setup_tunnel_servers.py"
        "ssh_tunnel_manager.py"
    )

    for script in "${scripts[@]}"; do
        if [[ -x "$script" ]]; then
            info "✅ $script is executable"
        else
            warn "⚠️  $script not executable, making executable..."
            chmod +x "$script"
        fi
    done
}

# Test if scripts contain sudo commands (privilege escalation fix)
test_sudo_commands() {
    log "Testing sudo command integration..."

    local bash_sudo_count=$(grep -c "sudo " setup_tunnel_servers.sh || echo "0")
    local python_sudo_count=$(grep -c "sudo " setup_tunnel_servers.py || echo "0")

    if [[ $bash_sudo_count -gt 10 ]]; then
        info "✅ Bash script has $bash_sudo_count sudo commands"
    else
        error "❌ Bash script may be missing sudo commands ($bash_sudo_count found)"
    fi

    if [[ $python_sudo_count -gt 10 ]]; then
        info "✅ Python script has $python_sudo_count sudo commands"
    else
        error "❌ Python script may be missing sudo commands ($python_sudo_count found)"
    fi
}

# Test SSH tunnel manager syntax
test_tunnel_manager() {
    log "Testing SSH tunnel manager syntax..."

    if python3 -m py_compile ssh_tunnel_manager.py; then
        info "✅ SSH tunnel manager syntax is valid"
    else
        error "❌ SSH tunnel manager has syntax errors"
    fi

    # Test help command
    if python3 ssh_tunnel_manager.py --help >/dev/null 2>&1; then
        info "✅ SSH tunnel manager help command works"
    else
        warn "⚠️  SSH tunnel manager help command failed"
    fi
}

# Test configuration file format
test_config_format() {
    log "Testing configuration file format..."

    if python3 -c "import json; json.load(open('servers_config.json'))" 2>/dev/null; then
        info "✅ servers_config.json is valid JSON"
    else
        error "❌ servers_config.json is invalid JSON"
    fi
}

# Test for common dependencies
test_dependencies() {
    log "Testing system dependencies..."

    local deps=("ssh" "ssh-keygen" "python3")

    for dep in "${deps[@]}"; do
        if command -v "$dep" >/dev/null 2>&1; then
            info "✅ $dep is available"
        else
            error "❌ $dep is missing"
        fi
    done
}

# Test dry run of setup script
test_dry_run() {
    log "Testing dry run functionality..."

    # Test bash script dry run
    if ./setup_tunnel_servers.sh --dry-run 127.0.0.1 >/dev/null 2>&1; then
        info "✅ Bash script dry run works"
    else
        warn "⚠️  Bash script dry run failed"
    fi

    # Test Python script dry run
    if python3 setup_tunnel_servers.py setup --dry-run 127.0.0.1 >/dev/null 2>&1; then
        info "✅ Python script dry run works"
    else
        warn "⚠️  Python script dry run failed"
    fi
}

# Test SSH key generation
test_ssh_key_generation() {
    log "Testing SSH key generation..."

    # Remove test key if exists
    rm -f test_tunnel_key test_tunnel_key.pub

    if python3 setup_tunnel_servers.py generate-keys --key-name test_tunnel_key >/dev/null 2>&1; then
        if [[ -f "test_tunnel_key" && -f "test_tunnel_key.pub" ]]; then
            info "✅ SSH key generation works"
            # Cleanup
            rm -f test_tunnel_key test_tunnel_key.pub
        else
            error "❌ SSH keys were not created"
        fi
    else
        error "❌ SSH key generation failed"
    fi
}

# Test IdentitiesOnly option
test_identities_only() {
    log "Testing IdentitiesOnly SSH option..."

    local bash_count=$(grep -c "IdentitiesOnly=yes" setup_tunnel_servers.sh || echo "0")
    local python_count=$(grep -c "IdentitiesOnly=yes" setup_tunnel_servers.py || echo "0")
    local manager_count=$(grep -c "IdentitiesOnly=yes" ssh_tunnel_manager.py || echo "0")

    if [[ $bash_count -gt 0 ]]; then
        info "✅ Bash script has IdentitiesOnly option ($bash_count instances)"
    else
        error "❌ Bash script missing IdentitiesOnly option"
    fi

    if [[ $python_count -gt 0 ]]; then
        info "✅ Python script has IdentitiesOnly option ($python_count instances)"
    else
        error "❌ Python script missing IdentitiesOnly option"
    fi

    if [[ $manager_count -gt 0 ]]; then
        info "✅ Tunnel manager has IdentitiesOnly option ($manager_count instances)"
    else
        error "❌ Tunnel manager missing IdentitiesOnly option"
    fi
}

# Main test execution
main() {
    echo "🧪 SSH Tunnel Setup Test Suite"
    echo "==============================="

    test_script_files
    test_permissions
    test_sudo_commands
    test_tunnel_manager
    test_config_format
    test_dependencies
    test_dry_run
    test_ssh_key_generation
    test_identities_only

    echo ""
    log "Test suite completed!"

    echo ""
    echo "📋 Next Steps:"
    echo "1. Configure your servers in servers_config.json"
    echo "2. Test with: python3 setup_tunnel_servers.py setup --dry-run <server-ip>"
    echo "3. Run actual setup: python3 setup_tunnel_servers.py setup-from-file servers_config.json"
    echo "4. Verify setup: python3 setup_tunnel_servers.py health-check"
}

# Run tests
main "$@"