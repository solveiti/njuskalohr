#!/usr/bin/env python3
"""
Configuration settings for Njuskalo sitemap-based store scraper.
"""

# Scraping settings
HEADLESS_MODE = True
BASE_URL = "https://www.njuskalo.hr"
SITEMAP_INDEX_URL = "https://www.njuskalo.hr/sitemap-index.xml"
STORES_SITEMAP_URL = "https://www.njuskalo.hr/sitemap-index-stores.xml"
STORES_XML_GZ_URL = "https://www.njuskalo.hr/sitemap-stores-01.xml.gz"

# Target category for filtering
AUTO_MOTO_CATEGORY_ID = 2

# Timing settings
MIN_DELAY = 2.0
MAX_DELAY = 5.0
SITEMAP_DELAY_MIN = 1.0
SITEMAP_DELAY_MAX = 3.0

# Browser settings
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"

# Output settings
OUTPUT_FILENAME = "njuskalo_stores.xlsx"
OUTPUT_DIRECTORY = "datadump"  # Directory for Excel file outputs
LOG_LEVEL = "INFO"

# Store page selectors
STORE_NAME_SELECTORS = [
    "h1",
    ".store-name",
    ".shop-name",
    ".entity-name"
]

STORE_ADDRESS_SELECTORS = [
    ".store-address",
    ".shop-address",
    ".address"
]

ENTITIES_COUNT_SELECTORS = [
    ".entities-count",
    ".ads-count",
    ".listings-count"
]

CATEGORY_LINK_SELECTORS = [
    "a[href*='categoryId=2']",
    "a[href*='/auti']",
    ".category-link"
]

# Request settings
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
STORE_URL_PATTERN = "/trgovina/"
