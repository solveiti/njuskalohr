# Njuskalo Sitemap Store Scraper

A Python web scraper that extracts store information from njuskalo.hr using a sitemap-based approach. This scraper focuses on finding stores that post in the "Auto moto" category (categoryId=2) and extracting their address and ad count information.

## 🎯 Purpose

This scraper is designed to:

1. Download the sitemap index XML from https://www.njuskalo.hr/sitemap-index.xml
2. Extract store-related sitemap URLs
3. Download and parse XML/XML.gz files to find store URLs (trgovina)
4. Visit each store page to scrape information
5. Check if stores post in categoryId 2 ("Auto moto" category)
6. Extract store address and number of ads from the entities-count class
7. Save all data to an Excel file and PostgreSQL database

## 🚀 Quick Start

### 1. Setup

Run the setup script to install dependencies:

```bash
chmod +x setup.sh
./setup.sh
```

This will:

- Install Google Chrome browser
- Create a Python virtual environment
- Install required Python packages

### 2. Database Setup (Optional but Recommended)

Set up PostgreSQL database for data persistence:

```bash
# Install PostgreSQL if not already installed
sudo apt-get install postgresql postgresql-contrib  # Ubuntu/Debian

# Run database setup
python setup_database.py
```

This will:

- Install PostgreSQL Python dependencies
- Create database and user
- Generate .env configuration file
- Test database connection

### 3. Run the Scraper

Start the scraper:

```bash
.venv/bin/python run_scraper.py
```

Or make it executable and run directly:

```bash
chmod +x run_scraper.py
./run_scraper.py
```

For command line options:

```bash
python run_scraper.py --help
python run_scraper.py --headless --max-stores 10  # Test run
python run_scraper.py --no-database  # Skip database storage
```

### 4. Database Management

Use the database management tool:

```bash
# View database statistics
python db_manager.py stats

# List valid stores
python db_manager.py list-valid --limit 20

# List invalid/failed URLs
python db_manager.py list-invalid

# Search stores
python db_manager.py search --query "auto"

# Export data to JSON
python db_manager.py export --output exported_data.json

# Create/recreate database tables
python db_manager.py create-tables
```

### 5. Test Sitemap Functionality

Before running the full scraper, you can test the sitemap functionality:

```bash
.venv/bin/python test_sitemap.py
```

## 📋 Features

- **Sitemap-based Discovery**: Uses official sitemaps to find all store URLs
- **Gzip Support**: Handles compressed XML sitemap files
- **Auto Moto Detection**: Specifically looks for stores posting in categoryId 2
- **Address Extraction**: Scrapes store addresses from various page layouts
- **Ad Count Extraction**: Gets number of ads from entities-count class
- **Human-like Behavior**: Random delays and browser settings to avoid detection
- **Excel Output**: Saves results in a structured Excel file
- **Comprehensive Logging**: Detailed logs for debugging and monitoring

## �️ Database Schema

The PostgreSQL database stores scraped data in the following structure:

### `scraped_stores` Table

| Column     | Type                     | Description                             |
| ---------- | ------------------------ | --------------------------------------- |
| id         | SERIAL PRIMARY KEY       | Auto-incrementing unique identifier     |
| url        | VARCHAR(2048) UNIQUE     | Store URL (unique constraint)           |
| results    | JSONB                    | Complete store data in JSON format      |
| is_valid   | BOOLEAN                  | Whether the URL is accessible and valid |
| created_at | TIMESTAMP WITH TIME ZONE | When the record was first created       |
| updated_at | TIMESTAMP WITH TIME ZONE | When the record was last updated        |

### JSONB Results Structure

The `results` column contains:

```json
{
  "url": "https://www.njuskalo.hr/trgovina/example",
  "name": "Store Name",
  "address": "Store Address",
  "ads_count": 123,
  "has_auto_moto": true,
  "categories": [
    {
      "text": "Auto i motori",
      "href": "/categoryi/auti-categoryId=2"
    }
  ],
  "error": null
}
```

### Database Features

- **Automatic Timestamps**: `created_at` and `updated_at` managed by triggers
- **Upsert Operations**: Updates existing records when URL already exists
- **GIN Indexing**: Fast JSON queries on the `results` column
- **Data Integrity**: URL uniqueness and proper foreign key constraints

## �🔧 Configuration

Main settings can be found in `config.py`:

- `HEADLESS_MODE`: Run browser in headless mode (True/False)
- `MIN_DELAY`/`MAX_DELAY`: Timing delays between actions
- `AUTO_MOTO_CATEGORY_ID`: Target category ID (default: 2)
- Various CSS selectors for different page elements

Database configuration is in `.env`:

```env
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=njuskalohr
DATABASE_USER=your_username
DATABASE_PASSWORD=your_password
```

## 📊 Output

The scraper generates an Excel file with the following columns:

- **Store Name**: Extracted store name
- **URL**: Store page URL
- **Address**: Store address information
- **Ads Count**: Number of ads posted by the store
- **Has Auto Moto**: Boolean indicating if store posts in Auto Moto category
- **Categories Count**: Number of categories the store posts in
- **Error**: Any errors encountered during scraping

## 🔍 Example Store

The scraper can handle stores like:

- https://www.njuskalo.hr/trgovina/zunicautomobili

## 📝 Workflow Details

1. **Sitemap Index Download**: Downloads the main sitemap index XML
2. **Sitemap Discovery**: Finds individual sitemap URLs, prioritizing store-related ones
3. **XML Processing**: Downloads and extracts (if gzipped) individual sitemap files
4. **URL Extraction**: Finds all URLs containing `/trgovina/` (store pages)
5. **Store Scraping**: Visits each store page and extracts:
   - Store name (from h1 or similar elements)
   - Address (from various address-related CSS classes)
   - Ad count (from entities-count class)
   - Category information (checking for categoryId=2 or auto/moto keywords)
6. **Data Export**: Saves all collected data to Excel file

## 🛠️ Technical Details

### Dependencies

- **selenium**: Web browser automation
- **requests**: HTTP requests for sitemap downloads
- **pandas**: Data manipulation and Excel export
- **lxml**: XML parsing
- **beautifulsoup4**: HTML parsing
- **webdriver-manager**: Automatic ChromeDriver management
- **psycopg2-binary**: PostgreSQL database adapter
- **python-dotenv**: Environment variable management

### Browser Settings

The scraper uses Chrome with anti-detection settings:

- Custom user agent
- Disabled automation indicators
- Human-like timing delays
- Proper window sizing

### Error Handling

- Retries for failed requests
- Graceful handling of missing page elements
- Comprehensive error logging
- Continues processing even if individual stores fail

## 🐛 Troubleshooting

### Common Issues

1. **Chrome not found**: Run the setup script to install Chrome
2. **Permission denied**: Don't run as root/sudo
3. **No stores found**: Check if website structure has changed
4. **Slow performance**: Adjust timing delays in config.py
5. **Database connection failed**:
   - Check PostgreSQL is running: `sudo systemctl status postgresql`
   - Verify credentials in `.env` file
   - Test connection: `python db_manager.py stats`
6. **psycopg2 installation failed**:
   - Install PostgreSQL development headers: `sudo apt-get install libpq-dev`
   - Use binary version: `pip install psycopg2-binary`

### Logs

Check these log files for detailed information:

- `sitemap_scraper.log`: Main scraper logs
- Console output: Real-time progress updates

### Testing

Use the test script to verify functionality:

```bash
.venv/bin/python test_sitemap.py
```

This tests sitemap downloading and parsing without running the full scraper.

## 📄 Files

- `njuskalo_sitemap_scraper.py`: Main scraper class
- `run_scraper.py`: Entry point script
- `config.py`: Configuration settings
- `test_sitemap.py`: Test script for sitemap functionality
- `setup.sh`: Installation and setup script
- `requirements.txt`: Python dependencies

## ⚖️ Legal Notice

This scraper is for educational and research purposes. Please respect njuskalo.hr's robots.txt and terms of service. Use responsibly and consider the website's server load.

## 🔄 Version History

- **v2.0**: Sitemap-based approach with Auto Moto category detection
- **v1.0**: Basic car listing scraper

For issues or improvements, please check the logs and ensure all dependencies are properly installed.
