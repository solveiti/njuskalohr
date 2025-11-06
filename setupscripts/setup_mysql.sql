-- Setup MySQL database and user for njuskalohr project
-- Run this script as MySQL root user: sudo mysql -u root < setup_mysql.sql

-- Create database
CREATE DATABASE IF NOT EXISTS njuskalohr CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user and grant privileges
CREATE USER IF NOT EXISTS 'hellios'@'localhost' IDENTIFIED BY '6hell6is6';
GRANT ALL PRIVILEGES ON njuskalohr.* TO 'hellios'@'localhost';
FLUSH PRIVILEGES;

-- Use the database
USE njuskalohr;

-- Show current databases and user to verify
SHOW DATABASES;
SELECT User, Host FROM mysql.user WHERE User = 'hellios';

-- Display success message
SELECT 'MySQL database and user setup completed successfully!' AS Status;