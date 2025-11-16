#!/usr/bin/env python3
"""
UUID Session Example for Njuskalo Stealth Publish

This example demonstrates how to use UUID-based Firefox sessions to avoid
confirmation codes on repeated logins.

Features:
- Persistent Firefox profiles stored in 'firefoxsessions' folder
- UUID-based session naming for API integration
- Consistent device fingerprinting to avoid detection
- Session metadata tracking (creation time, last used, etc.)

Usage Examples:
1. Generate a new session UUID automatically
2. Use a predefined UUID for API integration
3. Test with both visible and headless modes
"""

import os
import sys

# Ensure we're running in the virtual environment
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    # Try to load VENV_PATH from .env file
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    venv_path = '.venv'  # Default value

    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if line.strip() and not line.strip().startswith('#'):
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        if key.strip() == 'VENV_PATH':
                            venv_path = value.strip()
                            break

    venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), venv_path, 'bin', 'python3')
    if os.path.exists(venv_python):
        print(f"Restarting script in virtual environment: {venv_python}")
        os.execv(venv_python, [venv_python] + sys.argv)
    else:
        print(f"Warning: Virtual environment not found at {venv_python}")

import uuid
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from njuskalo_stealth_publish import NjuskaloStealthPublish


def example_auto_uuid():
    """Example 1: Auto-generate UUID session"""
    print("🆔 Example 1: Auto-generated UUID session")
    print("=" * 50)

    # UUID will be auto-generated if not provided
    stealth = NjuskaloStealthPublish(
        headless=True,
        use_tunnel=False,
        username="your_username",
        password="your_password",
        persistent=False,
        user_uuid=None  # Will auto-generate
    )

    print(f"Generated UUID: {stealth.user_uuid}")
    print(f"Session directory: {stealth.firefox_session_dir}")
    print()


def example_predefined_uuid():
    """Example 2: Use predefined UUID for API integration"""
    print("🎯 Example 2: Predefined UUID session")
    print("=" * 50)

    # Use a specific UUID (like from your API)
    api_user_uuid = "12345678-1234-5678-9abc-123456789012"

    stealth = NjuskaloStealthPublish(
        headless=True,
        use_tunnel=False,
        username="your_username",
        password="your_password",
        persistent=False,
        user_uuid=api_user_uuid
    )

    print(f"Using UUID: {stealth.user_uuid}")
    print(f"Session directory: {stealth.firefox_session_dir}")
    print()


def example_test_with_uuid():
    """Example 3: Complete test with UUID"""
    print("🧪 Example 3: Complete test with UUID session")
    print("=" * 50)

    # Generate a test UUID
    test_uuid = str(uuid.uuid4())
    print(f"Test UUID: {test_uuid}")

    stealth = NjuskaloStealthPublish(
        headless=False,  # Visible for testing
        use_tunnel=False,
        username="your_username",
        password="your_password",
        persistent=False,
        user_uuid=test_uuid
    )

    # Run the complete process
    success = stealth.run_stealth_publish()

    if success:
        print("✅ Session test successful!")
        print(f"Session data saved in: {stealth.firefox_session_dir}")
    else:
        print("❌ Session test failed!")

    print()


def example_command_line_usage():
    """Example 4: Command line usage patterns"""
    print("💻 Example 4: Command line usage")
    print("=" * 50)

    examples = [
        "# Run with auto-generated UUID:",
        "python3 njuskalo_stealth_publish.py --visible",
        "",
        "# Run with specific UUID (API integration):",
        "python3 njuskalo_stealth_publish.py --uuid 12345678-1234-5678-9abc-123456789012",
        "",
        "# Test with specific UUID:",
        "python3 test_stealth_publish.py --uuid 12345678-1234-5678-9abc-123456789012 --mode visible",
        "",
        "# Headless mode with UUID:",
        "python3 njuskalo_stealth_publish.py --uuid 12345678-1234-5678-9abc-123456789012",
    ]

    for example in examples:
        print(example)

    print()


def list_existing_sessions():
    """List all existing UUID sessions"""
    print("📋 Existing UUID sessions:")
    print("=" * 50)

    sessions_dir = Path("firefoxsessions")

    if not sessions_dir.exists():
        print("No sessions directory found.")
        return

    sessions = list(sessions_dir.iterdir())

    if not sessions:
        print("No existing sessions found.")
        return

    for session_dir in sessions:
        if session_dir.is_dir():
            session_file = session_dir / "session_info.json"
            if session_file.exists():
                import json
                try:
                    with open(session_file, 'r') as f:
                        info = json.load(f)

                    from datetime import datetime
                    created = datetime.fromtimestamp(info['created']).strftime('%Y-%m-%d %H:%M:%S')
                    last_used = datetime.fromtimestamp(info['last_used']).strftime('%Y-%m-%d %H:%M:%S')

                    print(f"UUID: {info['uuid']}")
                    print(f"  Username: {info['username']}")
                    print(f"  Created: {created}")
                    print(f"  Last used: {last_used}")
                    print(f"  Fingerprint: {info['fingerprint'][:16]}...")
                    print()
                except Exception as e:
                    print(f"Error reading session {session_dir.name}: {e}")


if __name__ == "__main__":
    print("🔥 Njuskalo Stealth Publish - UUID Session Examples")
    print("=" * 60)
    print()

    # Show existing sessions
    list_existing_sessions()

    # Run examples
    example_auto_uuid()
    example_predefined_uuid()
    example_command_line_usage()

    print("🚀 Ready to use UUID sessions!")
    print()
    print("Benefits of UUID sessions:")
    print("- ✅ No confirmation codes on repeated logins")
    print("- ✅ Persistent browser profiles")
    print("- ✅ API-friendly session management")
    print("- ✅ Consistent device fingerprinting")
    print("- ✅ Session metadata tracking")