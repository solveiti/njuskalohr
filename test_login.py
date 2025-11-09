#!/usr/bin/env python3
"""
Test login functionality for FastAPI authentication
"""
import os
import sys
import requests
import time

# Add current directory to path
sys.path.append(os.getcwd())

def test_login():
    """Test the complete login flow"""
    print("🔐 Testing FastAPI Login System")
    print("=" * 50)

    base_url = "http://localhost:8080"

    # Get configurable endpoints
    from dotenv import load_dotenv
    load_dotenv()
    login_endpoint = os.getenv("API_LOGIN_ENDPOINT", "/login")

    # Test environment variables first
    from dotenv import load_dotenv
    load_dotenv()

    print(f"Environment check:")
    print(f"  AUTH_USERNAME: {os.getenv('AUTH_USERNAME')}")
    print(f"  AUTH_PASSWORD: {os.getenv('AUTH_PASSWORD')}")
    print(f"  SECRET_KEY: {os.getenv('SECRET_KEY')[:20]}...")
    print()

    # Test credential verification
    try:
        from api import verify_credentials
        cred_test = verify_credentials("admin", "njuskalo2025")
        print(f"✅ Credential verification: {cred_test}")
    except Exception as e:
        print(f"❌ Credential verification error: {e}")
        return False

    # Test HTTP requests
    session = requests.Session()

    try:
        # Step 1: Test server accessibility
        print("\n1. Testing server accessibility...")
        health_response = session.get(f"{base_url}/health")
        print(f"   Health check: {health_response.status_code}")

        # Step 2: Access login page
        print("\n2. Testing login page...")
        login_page = session.get(f"{base_url}{login_endpoint}")
        print(f"   Login page: {login_page.status_code}")

        if login_page.status_code != 200:
            print(f"❌ Cannot access login page")
            return False

        # Step 3: Test root redirect
        print("\n3. Testing root redirect (should redirect to login)...")
        root_response = session.get(f"{base_url}/", allow_redirects=False)
        print(f"   Root access: {root_response.status_code}")
        if root_response.status_code == 302:
            print(f"   ✅ Properly redirected to: {root_response.headers.get('location')}")

        # Step 4: Test login POST
        print("\n4. Testing login POST...")
        login_data = {
            "username": "admin",
            "password": "njuskalo2025"
        }

        login_response = session.post(f"{base_url}{login_endpoint}", data=login_data, allow_redirects=False)
        print(f"   Login POST: {login_response.status_code}")

        if login_response.status_code == 302:
            print(f"   ✅ Login redirect to: {login_response.headers.get('location')}")
            print(f"   Cookies received: {list(session.cookies.keys())}")

            # Step 5: Test authenticated access to dashboard
            print("\n5. Testing authenticated dashboard access...")
            dashboard_response = session.get(f"{base_url}/njuskalo/dashboard", allow_redirects=False)
            print(f"   Dashboard access: {dashboard_response.status_code}")

            if dashboard_response.status_code == 200:
                print("   ✅ SUCCESS: Authentication working!")
                return True
            else:
                print(f"   ❌ Dashboard access failed: {dashboard_response.status_code}")
                if dashboard_response.status_code == 302:
                    print(f"   Still redirecting to: {dashboard_response.headers.get('location')}")
                return False
        else:
            print(f"   ❌ Login failed: {login_response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Is it running on port 8080?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_login()
    if success:
        print("\n🎉 Login system is working correctly!")
        print("You can now access: http://localhost:8080")
        print("Credentials: admin / njuskalo2025")
    else:
        print("\n💥 Login system has issues that need to be fixed.")
        sys.exit(1)