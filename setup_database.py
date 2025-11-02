#!/bin/bash
"""
Database Setup Script for Njuskalo Scraper

This script helps set up the PostgreSQL database for the Njuskalo scraper.
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

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")

    try:
        # Install psycopg2-binary and python-dotenv
        result = subprocess.run([sys.executable, "-m", "pip", "install", "psycopg2-binary", "python-dotenv"],
                              check=True, capture_output=True, text=True)
        print("✅ Python dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e.stderr}")
        return False

def check_postgresql():
    """Check if PostgreSQL is installed and running"""
    print("🔍 Checking PostgreSQL installation...")

    # Check if PostgreSQL is installed
    pg_version = run_command("psql --version", check=False)
    if not pg_version:
        print("❌ PostgreSQL is not installed")
        print("Please install PostgreSQL first:")
        print("  Ubuntu/Debian: sudo apt-get install postgresql postgresql-contrib")
        print("  CentOS/RHEL: sudo yum install postgresql-server postgresql-contrib")
        print("  macOS: brew install postgresql")
        return False

    print(f"✅ PostgreSQL found: {pg_version}")

    # Check if PostgreSQL is running
    pg_status = run_command("sudo systemctl is-active postgresql", check=False)
    if pg_status != "active":
        print("⚠️  PostgreSQL is not running, attempting to start...")
        start_result = run_command("sudo systemctl start postgresql", check=False)
        if start_result is None:
            print("❌ Failed to start PostgreSQL")
            return False
        print("✅ PostgreSQL started successfully")
    else:
        print("✅ PostgreSQL is running")

    return True

def create_database():
    """Create the database and user"""
    print("\n🗃️  Setting up database...")

    # Get database configuration
    db_name = input("Enter database name (default: njuskalohr): ").strip() or "njuskalohr"
    db_user = input("Enter database username (default: njuskalo_user): ").strip() or "njuskalo_user"
    db_password = getpass.getpass("Enter database password: ")

    if not db_password:
        print("❌ Password cannot be empty")
        return False

    try:
        # Create user and database
        print("Creating database user and database...")

        # Commands to run as postgres user
        commands = [
            f"CREATE USER {db_user} WITH PASSWORD '{db_password}';",
            f"CREATE DATABASE {db_name} OWNER {db_user};",
            f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};"
        ]

        for cmd in commands:
            psql_cmd = f'sudo -u postgres psql -c "{cmd}"'
            result = run_command(psql_cmd, check=False)
            if result is None:
                print(f"Warning: Command may have failed: {cmd}")
            else:
                print(f"✅ Executed: {cmd}")

        print("✅ Database and user created successfully")

        # Create .env file
        create_env_file(db_name, db_user, db_password)

        return True

    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def create_env_file(db_name, db_user, db_password):
    """Create .env file with database configuration"""
    print("📝 Creating .env file...")

    env_content = f"""# PostgreSQL Database Configuration
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME={db_name}
DATABASE_USER={db_user}
DATABASE_PASSWORD={db_password}
DATABASE_URL=postgresql://{db_user}:{db_password}@localhost:5432/{db_name}
"""

    env_path = Path(".env")

    # Backup existing .env file
    if env_path.exists():
        backup_path = Path(".env.backup")
        env_path.rename(backup_path)
        print(f"⚠️  Existing .env backed up to {backup_path}")

    # Write new .env file
    with open(env_path, "w") as f:
        f.write(env_content)

    # Set secure permissions
    os.chmod(env_path, 0o600)

    print("✅ .env file created successfully")

def test_connection():
    """Test database connection"""
    print("\n🔬 Testing database connection...")

    try:
        # Import and test database connection
        from database import NjuskaloDatabase

        with NjuskaloDatabase() as db:
            db.create_tables()
            print("✅ Database connection successful")
            print("✅ Database tables created")

            # Test basic operations
            stats = db.get_database_stats()
            print(f"📊 Database stats: {stats}")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all dependencies are installed")
        return False
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Please check your database configuration")
        return False

def main():
    """Main setup function"""
    print("🚀 Njuskalo Scraper Database Setup")
    print("=" * 40)

    # Step 1: Install Python dependencies
    if not install_dependencies():
        print("❌ Setup failed at dependency installation")
        return False

    # Step 2: Check PostgreSQL
    if not check_postgresql():
        print("❌ Setup failed at PostgreSQL check")
        return False

    # Step 3: Create database
    print("\nWould you like to create a new database? (y/n)")
    create_db = input().strip().lower() in ['y', 'yes']

    if create_db:
        if not create_database():
            print("❌ Setup failed at database creation")
            return False
    else:
        print("Skipping database creation")
        print("Make sure to create a .env file with your database configuration")

    # Step 4: Test connection
    if os.path.exists(".env"):
        if not test_connection():
            print("❌ Setup failed at connection test")
            return False
    else:
        print("⚠️  No .env file found, skipping connection test")

    print("\n🎉 Database setup completed successfully!")
    print("\nNext steps:")
    print("1. Run the scraper: python run_scraper.py")
    print("2. View database stats: python db_manager.py stats")
    print("3. List stored data: python db_manager.py list-valid")

    return True

if __name__ == "__main__":
    main()