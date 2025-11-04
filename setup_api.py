#!/usr/bin/env python3
"""
Setup script for Njuskalo Scraper API with Celery and Redis
"""

import os
import sys
import subprocess
import getpass
from pathlib import Path

def run_command(command, check=True):
    """Run a shell command"""
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command '{command}': {e.stderr}")
        return None

def check_redis():
    """Check if Redis is installed and running"""
    print("🔍 Checking Redis installation...")

    # Check if Redis is installed
    redis_version = run_command("redis-server --version", check=False)
    if not redis_version:
        print("❌ Redis is not installed")
        print("Installing Redis...")
        print("Ubuntu/Debian: sudo apt-get install redis-server")
        install_redis = input("Would you like to install Redis now? (y/n): ").strip().lower()
        if install_redis in ['y', 'yes']:
            result = run_command("sudo apt-get update && sudo apt-get install -y redis-server", check=False)
            if result is None:
                print("❌ Failed to install Redis")
                return False
        else:
            return False

    print(f"✅ Redis found: {redis_version}")

    # Check if Redis is running
    redis_ping = run_command("redis-cli ping", check=False)
    if redis_ping != "PONG":
        print("⚠️  Redis is not running, attempting to start...")
        start_result = run_command("sudo systemctl start redis-server", check=False)
        if start_result is None:
            print("❌ Failed to start Redis")
            return False
        print("✅ Redis started successfully")
    else:
        print("✅ Redis is running")

    return True

def install_api_dependencies():
    """Install API-specific dependencies"""
    print("📦 Installing API dependencies...")

    try:
        # Install FastAPI, Celery, and related packages
        api_packages = [
            "fastapi>=0.104.1",
            "uvicorn[standard]>=0.24.0",
            "celery>=5.3.4",
            "redis>=5.0.1",
            "flower>=2.0.1",
            "pydantic>=2.5.0",
            "python-multipart>=0.0.6",
            "jinja2>=3.1.2",
            "aiofiles>=23.2.1"
        ]

        for package in api_packages:
            print(f"Installing {package}...")
            result = subprocess.run([sys.executable, "-m", "pip", "install", package],
                                  check=True, capture_output=True, text=True)

        print("✅ API dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install API dependencies: {e.stderr}")
        return False

def setup_environment():
    """Set up environment configuration"""
    print("📝 Setting up environment configuration...")

    env_path = Path(".env")

    if env_path.exists():
        print("⚠️  .env file already exists")
        overwrite = input("Would you like to overwrite it? (y/n): ").strip().lower()
        if overwrite not in ['y', 'yes']:
            print("Keeping existing .env file")
            return True

    # Get configuration values
    print("Please provide configuration values:")

    # Database configuration
    db_host = input("Database host (default: localhost): ").strip() or "localhost"
    db_port = input("Database port (default: 5432): ").strip() or "5432"
    db_name = input("Database name (default: njuskalohr): ").strip() or "njuskalohr"
    db_user = input("Database user (default: njuskalo_user): ").strip() or "njuskalo_user"
    db_password = getpass.getpass("Database password: ")

    # Redis configuration
    redis_host = input("Redis host (default: localhost): ").strip() or "localhost"
    redis_port = input("Redis port (default: 6379): ").strip() or "6379"
    redis_db = input("Redis database (default: 0): ").strip() or "0"

    # API configuration
    api_host = input("API host (default: 0.0.0.0): ").strip() or "0.0.0.0"
    api_port = input("API port (default: 8000): ").strip() or "8000"

    # Create .env content
    env_content = f"""# PostgreSQL Database Configuration
DATABASE_HOST={db_host}
DATABASE_PORT={db_port}
DATABASE_NAME={db_name}
DATABASE_USER={db_user}
DATABASE_PASSWORD={db_password}
DATABASE_URL=postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}

# Redis Configuration (for Celery)
REDIS_HOST={redis_host}
REDIS_PORT={redis_port}
REDIS_DB={redis_db}
REDIS_URL=redis://{redis_host}:{redis_port}/{redis_db}

# Celery Configuration
CELERY_BROKER_URL=redis://{redis_host}:{redis_port}/{redis_db}
CELERY_RESULT_BACKEND=redis://{redis_host}:{redis_port}/{redis_db}

# FastAPI Configuration
API_HOST={api_host}
API_PORT={api_port}
API_RELOAD=True
"""

    # Write .env file
    with open(env_path, "w") as f:
        f.write(env_content)

    # Set secure permissions
    os.chmod(env_path, 0o600)

    print("✅ .env file created successfully")
    return True

def test_api_setup():
    """Test the API setup"""
    print("\n🔬 Testing API setup...")

    try:
        # Test imports
        print("Testing imports...")
        import fastapi
        import celery
        import redis
        import uvicorn
        print("✅ All required packages imported successfully")

        # Test Redis connection
        print("Testing Redis connection...")
        import redis as redis_client
        r = redis_client.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis connection successful")

        # Test database connection (if configured)
        if os.path.exists('.env'):
            print("Testing database connection...")
            from database import NjuskaloDatabase
            with NjuskaloDatabase() as db:
                stats = db.get_database_stats()
                print("✅ Database connection successful")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Setup test failed: {e}")
        return False

def create_systemd_services():
    """Create systemd service files for production deployment"""
    print("\n🔧 Creating systemd service files...")

    app_dir = os.getcwd()
    user = os.getenv('USER', 'ubuntu')

    # Celery worker service
    worker_service = f"""[Unit]
Description=Njuskalo Celery Worker
After=network.target

[Service]
Type=forking
User={user}
Group={user}
WorkingDirectory={app_dir}
Environment=PATH={app_dir}/.venv/bin
ExecStart={app_dir}/.venv/bin/celery -A celery_config worker --loglevel=info --pidfile={app_dir}/celery_worker.pid --detach
ExecStop=/bin/kill -s TERM $MAINPID
PIDFile={app_dir}/celery_worker.pid
Restart=always

[Install]
WantedBy=multi-user.target
"""

    # Celery beat service
    beat_service = f"""[Unit]
Description=Njuskalo Celery Beat
After=network.target

[Service]
Type=forking
User={user}
Group={user}
WorkingDirectory={app_dir}
Environment=PATH={app_dir}/.venv/bin
ExecStart={app_dir}/.venv/bin/celery -A celery_config beat --loglevel=info --pidfile={app_dir}/celery_beat.pid --detach
ExecStop=/bin/kill -s TERM $MAINPID
PIDFile={app_dir}/celery_beat.pid
Restart=always

[Install]
WantedBy=multi-user.target
"""

    # FastAPI service
    api_service = f"""[Unit]
Description=Njuskalo FastAPI
After=network.target

[Service]
Type=simple
User={user}
Group={user}
WorkingDirectory={app_dir}
Environment=PATH={app_dir}/.venv/bin
ExecStart={app_dir}/.venv/bin/python api.py
Restart=always

[Install]
WantedBy=multi-user.target
"""

    # Write service files
    services_dir = Path("systemd")
    services_dir.mkdir(exist_ok=True)

    (services_dir / "njuskalo-worker.service").write_text(worker_service)
    (services_dir / "njuskalo-beat.service").write_text(beat_service)
    (services_dir / "njuskalo-api.service").write_text(api_service)

    print("✅ Systemd service files created in ./systemd/")
    print("To install them:")
    print("  sudo cp systemd/*.service /etc/systemd/system/")
    print("  sudo systemctl daemon-reload")
    print("  sudo systemctl enable njuskalo-worker njuskalo-beat njuskalo-api")
    print("  sudo systemctl start njuskalo-worker njuskalo-beat njuskalo-api")

def main():
    """Main setup function"""
    print("🚀 Njuskalo Scraper API Setup")
    print("=" * 50)

    # Check if running in virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  It's recommended to run this in a virtual environment")
        continue_setup = input("Continue anyway? (y/n): ").strip().lower()
        if continue_setup not in ['y', 'yes']:
            print("Please activate your virtual environment and run again")
            return False

    # Step 1: Check Redis
    if not check_redis():
        print("❌ Setup failed at Redis check")
        return False

    # Step 2: Install API dependencies
    if not install_api_dependencies():
        print("❌ Setup failed at API dependency installation")
        return False

    # Step 3: Set up environment
    if not setup_environment():
        print("❌ Setup failed at environment setup")
        return False

    # Step 4: Test setup
    if not test_api_setup():
        print("❌ Setup failed at testing phase")
        return False

    # Step 5: Create systemd services (optional)
    create_services = input("\nWould you like to create systemd service files? (y/n): ").strip().lower()
    if create_services in ['y', 'yes']:
        create_systemd_services()

    print("\n🎉 API setup completed successfully!")
    print("\nNext steps:")
    print("1. Start services: ./start_all.sh")
    print("2. Or start individually:")
    print("   - Worker: ./start_worker.sh")
    print("   - Beat: ./start_beat.sh")
    print("   - API: ./start_api.sh")
    print("3. Open dashboard: http://localhost:8000")
    print("4. View API docs: http://localhost:8000/docs")
    print("5. Monitor tasks: http://localhost:5555 (Flower)")
    print("\nUseful commands:")
    print("- View logs: tail -f celery_worker.log celery_beat.log")
    print("- Stop services: ./stop_all.sh")
    print("- Monitor Redis: redis-cli monitor")

    return True

if __name__ == "__main__":
    main()