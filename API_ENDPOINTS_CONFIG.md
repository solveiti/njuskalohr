# Configurable API Endpoints

This update introduces configurable API endpoints for the FastAPI dashboard template, allowing you to customize the API URLs through environment variables.

## Configuration

### Environment Variables

Add the following configuration to your `.env` file:

```bash
# API Endpoints Configuration (for frontend)
API_BASE_URL=http://localhost:8000
API_SCRAPE_START_ENDPOINT=/scrape/start
API_SCRAPE_TUNNEL_ENDPOINT=/scrape/tunnel
API_SCRAPE_TEST_ENDPOINT=/scrape/test
API_SCRAPE_STATUS_ENDPOINT=/scrape/status
API_SCRAPE_CANCEL_ENDPOINT=/scrape/cancel
API_CLEANUP_ENDPOINT=/cleanup/excel-files
API_TASKS_RECENT_ENDPOINT=/tasks/recent
API_DATA_SEND_ENDPOINT=/api/send-data
```

### Default Values

If not specified in the `.env` file, the following default values are used:

- `API_BASE_URL`: `http://localhost:8000`
- `API_SCRAPE_START_ENDPOINT`: `/scrape/start`
- `API_SCRAPE_TUNNEL_ENDPOINT`: `/scrape/tunnel`
- `API_SCRAPE_TEST_ENDPOINT`: `/scrape/test`
- `API_SCRAPE_STATUS_ENDPOINT`: `/scrape/status`
- `API_SCRAPE_CANCEL_ENDPOINT`: `/scrape/cancel`
- `API_CLEANUP_ENDPOINT`: `/cleanup/excel-files`
- `API_TASKS_RECENT_ENDPOINT`: `/tasks/recent`
- `API_DATA_SEND_ENDPOINT`: `/api/send-data`

## Features

### Enhanced Dashboard

The dashboard template now includes:

1. **Original Controls:**

   - Start Scraping (with configurable max stores and database options)
   - Test Scraper
   - Cleanup Files

2. **New Advanced Controls:**
   - **Enhanced Tunnel Scraping**: Secure scraping with SSH tunnels and enhanced features
   - **API Data Sender**: Send dealership data to external APIs with configurable date and minimum vehicle filters

### API Endpoint Configuration

The template dynamically uses the configured endpoints through JavaScript:

```javascript
window.API_CONFIG = {
  baseUrl: "{{ api_config.base_url }}",
  endpoints: {
    scrapeStart: "{{ api_config.endpoints.scrape_start }}",
    scrapeTunnel: "{{ api_config.endpoints.scrape_tunnel }}",
    // ... other endpoints
  },
};
```

### Benefits

1. **Flexibility**: Easily change API endpoints without modifying template code
2. **Environment-Specific Configuration**: Different endpoints for development, staging, and production
3. **Proxy-Friendly**: Support for reverse proxies and custom routing
4. **Maintainability**: Centralized endpoint configuration

## Usage Examples

### Development Environment

```bash
API_BASE_URL=http://localhost:8000
API_SCRAPE_START_ENDPOINT=/scrape/start
```

### Production with Reverse Proxy

```bash
API_BASE_URL=https://yourdomain.com/api
API_SCRAPE_START_ENDPOINT=/v1/scrape/start
API_SCRAPE_TUNNEL_ENDPOINT=/v1/scrape/tunnel
```

### Custom API Gateway

```bash
API_BASE_URL=https://api-gateway.example.com
API_SCRAPE_START_ENDPOINT=/njuskalo/scrape/start
API_SCRAPE_TUNNEL_ENDPOINT=/njuskalo/scrape/tunnel
```

## Implementation Details

### FastAPI Changes

- Modified root endpoint (`/`) to pass `api_config` to the template
- Added environment variable reading with fallback defaults
- No breaking changes to existing API endpoints

### Template Changes

- Added JavaScript configuration injection
- Updated all fetch calls to use configurable endpoints
- Added new UI controls for tunnel scraping and API data sending
- Maintained backward compatibility with existing functionality

### New Controls

**Enhanced Tunnel Scraping:**

- Uses existing scraper options (max stores, database save)
- Calls `/scrape/tunnel` endpoint
- Provides secure scraping with SSH tunnel protection

**API Data Sender:**

- Configurable scraping date (defaults to today)
- Minimum vehicles threshold (default: 5)
- Calls `/api/send-data` endpoint
- Sends dealership data to external Dober Avto API

## Migration

Existing installations will continue to work without changes. To enable custom endpoints:

1. Add the API endpoint configuration to your `.env` file
2. Restart the FastAPI application
3. The dashboard will automatically use the configured endpoints

No code changes are required for basic usage - the system uses sensible defaults.
