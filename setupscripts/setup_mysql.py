#!/usr/bin/env python3
"""
MySQL Database Setup Script for Njuskalo Scraper

This script helps set up the MySQL database for the Njuskalo scraper.
It replaces the PostgreSQL setup with MySQL/MariaDB configuration.
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
        # Install PyMySQL and python-dotenv
        result = subprocess.run([sys.executable, "-m", "pip", "install", "PyMySQL>=1.1.0", "python-dotenv"],
                              check=True, capture_output=True, text=True)
        print("✅ Python dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e.stderr}")
        return False

def check_mysql():
    """Check if MySQL/MariaDB is installed and running"""
    print("🔍 Checking MySQL/MariaDB installation...")

    # Check if MySQL or MariaDB is installed
    mysql_version = run_command("mysql --version", check=False)
    mariadb_version = run_command("mariadb --version", check=False)

    if not mysql_version and not mariadb_version:
        print("❌ MySQL/MariaDB is not installed")
        print("Please install MySQL or MariaDB first:")
        print("  Ubuntu/Debian: sudo apt-get install mysql-server")
        print("  CentOS/RHEL: sudo yum install mysql-server")
        print("  Arch/Manjaro: sudo pacman -S mariadb")
        print("  macOS: brew install mysql")
        return False

    if mysql_version:
        print(f"✅ MySQL found: {mysql_version}")
        service_name = "mysql"
    else:
        print(f"✅ MariaDB found: {mariadb_version}")
        service_name = "mariadb"

    # Check if MySQL/MariaDB is running
    mysql_status = run_command(f"sudo systemctl is-active {service_name}", check=False)
    if mysql_status != "active":
        print(f"⚠️  {service_name} is not running, attempting to start...")
        start_result = run_command(f"sudo systemctl start {service_name}", check=False)
        if start_result is None:
            print(f"❌ Failed to start {service_name}")
            return False
        print(f"✅ {service_name} started successfully")
    else:
        print(f"✅ {service_name} is running")

    return True

def create_database():
    """Create the database and user"""
    print("\n🗃️  Setting up database...")

    # Get database configuration
    db_name = input("Enter database name (default: njuskalohr): ").strip() or "njuskalohr"
    db_user = input("Enter database username (default: hellios): ").strip() or "hellios"
    db_password = getpass.getpass("Enter database password: ")

    if not db_password:
        print("❌ Password cannot be empty")
        return False

    try:
        print("Creating database user and database...")
        print("Please enter your MySQL root password when prompted...")

        # Create SQL commands
        sql_commands = f"""
CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '{db_user}'@'localhost' IDENTIFIED BY '{db_password}';
GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'localhost';
FLUSH PRIVILEGES;
SHOW DATABASES;
SELECT User, Host FROM mysql.user WHERE User = '{db_user}';
        """.strip()

        # Write SQL to temporary file
        sql_file = Path("temp_setup.sql")
        with open(sql_file, "w") as f:
            f.write(sql_commands)

        # Execute SQL file
        mysql_cmd = f"sudo mysql -u root < {sql_file}"
        result = subprocess.run(mysql_cmd, shell=True, check=False)

        # Clean up
        sql_file.unlink(missing_ok=True)

        if result.returncode == 0:
            print("✅ Database and user created successfully")
            # Create .env file
            create_env_file(db_name, db_user, db_password)
            return True
        else:
            print("❌ Failed to create database and user")
            return False

    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def create_env_file(db_name, db_user, db_password):
    """Create .env file with database configuration"""
    print("📝 Creating .env file...")

    env_content = f"""# MySQL Database Configuration
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_NAME={db_name}
DATABASE_USER={db_user}
DATABASE_PASSWORD={db_password}
DATABASE_URL=mysql+pymysql://{db_user}:{db_password}@localhost:3306/{db_name}

# Redis Configuration (for Celery)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_URL=redis://localhost:6379/0

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# FastAPI Configuration
API_HOST=0.0.0.0
API_PORT=8080
API_DEBUG=true
API_SECRET_KEY=your-secret-key-here-change-in-production

# Scraper Configuration
SCRAPER_DELAY=1
SCRAPER_TIMEOUT=30
SCRAPER_USER_AGENT=Mozilla/5.0 (compatible; NjuskaloScraper/1.0)

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/scraper.log
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

def setup_existing_mysql():
    """Setup for existing MySQL installation"""
    print("\n🔧 Setting up existing MySQL database...")

    print("Since you already have MySQL installed, you can:")
    print("1. Run the setup_mysql.sql script manually")
    print("2. Create the database configuration manually")
    print("3. Use the migration script to transfer PostgreSQL data")

    choice = input("\nChoose an option (1/2/3) or press Enter to skip: ").strip()

    if choice == "1":
        print("\nTo run the setup script:")
        print("sudo mysql -u root < setup_mysql.sql")
        print("\nAfter running the script, your database will be ready.")

    elif choice == "2":
        return create_database()

    elif choice == "3":
        print("\nTo migrate PostgreSQL data:")
        print("python migrate_pg_to_mysql.py")
        print("\nMake sure both PostgreSQL and MySQL are running before migration.")

    return True

def main():
    """Main setup function"""
    print("🚀 Njuskalo Scraper MySQL Database Setup")
    print("=" * 45)

    # Step 1: Install Python dependencies
    if not install_dependencies():
        print("❌ Setup failed at dependency installation")
        return False

    # Step 2: Check MySQL
    if not check_mysql():
        print("❌ Setup failed at MySQL check")
        return False

    # Step 3: Setup database
    print("\nDatabase setup options:")
    print("1. Create new database and user")
    print("2. Use existing database (manual setup)")
    print("3. Run migration from PostgreSQL")

    choice = input("Choose an option (1/2/3): ").strip()

    if choice == "1":
        if not create_database():
            print("❌ Setup failed at database creation")
            return False
    elif choice == "2":
        if not setup_existing_mysql():
            print("❌ Setup failed at existing MySQL setup")
            return False
    elif choice == "3":
        print("Make sure to run the migration script after this setup:")
        print("python migrate_pg_to_mysql.py")
    else:
        print("Invalid choice. Skipping database creation.")

    # Step 4: Test connection
    if os.path.exists(".env"):
        print("\nWould you like to test the database connection? (y/n)")
        test_choice = input().strip().lower() in ['y', 'yes']

        if test_choice:
            if not test_connection():
                print("❌ Setup failed at connection test")
                return False
    else:
        print("⚠️  No .env file found, skipping connection test")

    print("\n🎉 MySQL database setup completed successfully!")
    print("\nNext steps:")
    print("1. If migrating from PostgreSQL: python migrate_pg_to_mysql.py")
    print("2. Run the API server: python api.py")
    print("3. Start Celery worker: celery -A celery_config worker --loglevel=info")
    print("4. Start Celery beat: celery -A celery_config beat --loglevel=info")
    print("5. Run the scraper: python run_scraper.py")

    return True

if __name__ == "__main__":
    main()