#!/bin/bash

# Test script for privilege handling
# This tests the same functions that are used in the setup scripts

echo "=== Privilege Handling Test ==="
echo "Testing the privilege detection and execution system..."
echo

# Import the privilege handling functions
check_privileges() {
    if [ "$EUID" -eq 0 ]; then
        echo "root"
    elif sudo -n true 2>/dev/null; then
        echo "sudo"
    else
        echo "none"
    fi
}

run_privileged() {
    local privilege_level=$(check_privileges)

    case "$privilege_level" in
        "root")
            echo "[ROOT] Running: $*"
            "$@"
            ;;
        "sudo")
            echo "[SUDO] Running: sudo $*"
            sudo "$@"
            ;;
        "none")
            echo "[ERROR] Insufficient privileges to run: $*"
            echo "This script requires either:"
            echo "  1. Root user access, OR"
            echo "  2. User with passwordless sudo privileges"
            echo
            echo "To configure passwordless sudo:"
            echo "  sudo visudo"
            echo "  Add line: $(whoami) ALL=(ALL) NOPASSWD:ALL"
            return 1
            ;;
    esac
}

# Test privilege detection
echo "1. Testing privilege detection..."
PRIVILEGE_LEVEL=$(check_privileges)
echo "   Detected privilege level: $PRIVILEGE_LEVEL"
echo

# Test whoami command (should work for everyone)
echo "2. Testing basic command execution..."
run_privileged whoami
echo

# Test privileged command (requires root/sudo)
echo "3. Testing privileged command (reading /etc/shadow first line)..."
if run_privileged head -1 /etc/shadow >/dev/null 2>&1; then
    echo "   ✓ Privileged command executed successfully"
else
    echo "   ✗ Privileged command failed - check your configuration"
fi
echo

# Test package manager access (if available)
echo "4. Testing package manager access..."
if command -v apt-get >/dev/null 2>&1; then
    echo "   Testing apt-get update (dry run)..."
    if run_privileged apt-get update --dry-run >/dev/null 2>&1; then
        echo "   ✓ Package manager access confirmed"
    else
        echo "   ✗ Package manager access failed"
    fi
elif command -v yum >/dev/null 2>&1; then
    echo "   Testing yum check-update..."
    if run_privileged yum check-update >/dev/null 2>&1; then
        echo "   ✓ Package manager access confirmed"
    else
        echo "   ✗ Package manager access failed"
    fi
else
    echo "   No recognized package manager found (apt-get/yum)"
fi

echo
echo "=== Test Complete ==="
echo "If all tests passed, your system is properly configured for the setup scripts."
echo