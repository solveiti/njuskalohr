# Njuskalo HR — Store Scraper

A Python scraper for njuskalo.hr that discovers car dealership stores via the sitemap XML, visits each store page, counts active ads by vehicle type (new / used / test), tracks count changes between runs to infer sold/removed listings, and exports results to Excel.

---

## Table of Contents

1. [Overview](#overview)
2. [Project Structure](#project-structure)
3. [Installation — Ubuntu remote server](#installation--ubuntu-remote-server)
4. [Configuration](#configuration)
5. [Running the Scraper](#running-the-scraper)
6. [How It Works](#how-it-works)
7. [Vehicle Type Detection](#vehicle-type-detection)
8. [Active vs. Sold Tracking](#active-vs-sold-tracking)
9. [Database](#database)
10. [Exporting to Excel](#exporting-to-excel)
11. [SSH Tunnel Support](#ssh-tunnel-support)
12. [Troubleshooting](#troubleshooting)

---

## Overview

The scraper:

- Downloads the njuskalo.hr sitemap XML to discover all store (`/trgovina/`) URLs
- Visits each store page filtered to the Auto Moto category (`categoryId=2`)
- Detects whether the store sells vehicles and counts ads by type: **new**, **used**, **test**
- Records a **snapshot** on every run — the delta between runs reveals how many ads were removed (sold) since last time
- Saves everything to a local SQLite file and optionally exports to Excel

---

## Project Structure

```
njuskalohr/
├── run.sh                        # Main launcher (use this)
├── run_scraper.py                # CLI entry point
│
├── enhanced_tunnel_scraper.py    # Scraper with SSH tunnel support (default mode)
├── enhanced_njuskalo_scraper.py  # Scraper without tunnels
├── njuskalo_sitemap_scraper.py   # Base sitemap scraper
├── ssh_tunnel_manager.py         # SSH SOCKS5 tunnel manager
│
├── database.py                   # SQLite schema + all DB operations
├── db_helper.py                  # Simplified DB access (read queries)
├── db_manager.py                 # DB utility helpers
├── models.py                     # Pydantic data models
├── config.py                     # Scraper settings / selectors
│
├── export_db_to_excel.py         # Export DB to .xlsx
├── sentry_helper.py              # Optional Sentry error tracking
├── test_xvfb_firefox.py          # Verify Firefox + VNC/display setup
│
├── tunnel_config.json            # SSH tunnel definitions
├── .env                          # Environment variables (not committed)
├── njuskalo.db                   # SQLite database (auto-created on first run)
└── datadump/                     # Excel export output directory
```

---

## Installation — Ubuntu remote server

### 1. System packages

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
```

### 2. Firefox and GeckoDriver

Ubuntu's `geckodriver` package is often outdated. Install the latest release manually:

```bash
# Firefox
sudo apt install -y firefox

# GeckoDriver — download latest release from GitHub
GECKO_VER=$(curl -s https://api.github.com/repos/mozilla/geckodriver/releases/latest \
            | grep '"tag_name"' | cut -d'"' -f4)
curl -L "https://github.com/mozilla/geckodriver/releases/download/${GECKO_VER}/geckodriver-${GECKO_VER}-linux64.tar.gz" \
  | sudo tar -xz -C /usr/local/bin
sudo chmod +x /usr/local/bin/geckodriver
geckodriver --version   # verify
```

### 3. VNC display

The scraper requires a running X display. The remote server already has Xvfb + VNC configured on screen `:3` — **no extra setup needed**.

If you ever need to verify the display is available:

```bash
DISPLAY=:3 xdpyinfo | head -5
```

### 4. Clone the repository

```bash
git clone <repo-url> njuskalohr
cd njuskalohr
```

### 5. Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 6. Configuration

Copy the example env file and edit it:

```bash
cp .env.example .env
nano .env
```

The only required change is confirming `DISPLAY_NUM` matches the VNC screen on your server (default is `:3`). The SQLite database is created automatically — no database server needed.

---

## Configuration

`.env` reference:

```env
# SQLite database file path (default: njuskalo.db in project root)
DATABASE_PATH=njuskalo.db

# X display used by Firefox — must match the running VNC screen
DISPLAY_NUM=:3

# Njuskalo URLs (defaults are fine)
NJUSKALO_BASE_URL=https://www.njuskalo.hr
NJUSKALO_SITEMAP_INDEX_URL=https://www.njuskalo.hr/sitemap-index.xml

# Optional: Sentry error tracking
SENTRY_DSN=
SENTRY_ENVIRONMENT=production
```

`run.sh` loads `.env` automatically and exports `DISPLAY` from `DISPLAY_NUM` before starting Python. If `DISPLAY` is already set in the shell environment it is left unchanged.

---

## Running the Scraper

Always use `run.sh` — it activates the venv, loads `.env`, and sets the display.

### Detached screen run (default)

`run.sh` now starts in a detached `screen` session automatically when launched from a normal shell.

```bash
./run.sh                   # starts detached session "njuskalo"
screen -ls                 # list running sessions
screen -d -r njuskalo      # attach safely (detaches elsewhere if needed)
screen -ls                 # list running sessions

# Ctrl+A then D            # detach — scraper keeps running
screen -d -r njuskalo      # reattach later
```

Optional flags:

```bash
./run.sh --screen-session scraper-enhanced --mode enhanced
./run.sh --no-screen --mode enhanced    # run directly in current terminal
```

### Common options

```bash
./run.sh                          # tunnel mode, all stores (default)
./run.sh --mode enhanced          # enhanced mode, no SSH tunnels
./run.sh --mode basic             # basic sitemap scrape
./run.sh --max-stores 10          # limit to 10 stores (for testing)
./run.sh --no-tunnels             # disable SSH tunnels
./run.sh --no-database            # print results to stdout only, no DB write
./run.sh --verbose                # debug logging
./run.sh --help                   # full option list
```

### Scraping modes

| Mode       | Command                    | Description                                                 |
| ---------- | -------------------------- | ----------------------------------------------------------- |
| `tunnel`   | `./run.sh`                 | Enhanced scraper routed through SSH SOCKS5 tunnel (default) |
| `enhanced` | `./run.sh --mode enhanced` | Enhanced scraper, direct connection                         |
| `basic`    | `./run.sh --mode basic`    | Basic sitemap scraper, no vehicle type counting             |

---

## How It Works

### Step 1 — URL discovery

On first run (or when the database is empty / stale) the scraper downloads the sitemap XML from njuskalo.hr and extracts all `/trgovina/` store URLs. New URLs are inserted into the `scraped_stores` table.

On subsequent runs, if the database was updated recently it skips the XML step and re-scrapes the known auto-moto store URLs instead.

### Step 2 — Store scraping

For each URL the scraper:

1. Appends `?categoryId=2` to filter the page to Auto Moto ads only
2. Checks for auto-moto category indicators (links, keywords)
3. If the store sells vehicles, counts ad listings by type (new / used / test) across all pages (up to 20 pages of pagination)
4. Saves the result to `scraped_stores` (upsert) and appends a row to `store_snapshots`

### Step 3 — Anti-detection

- Randomised Firefox user-agent and window size on every launch
- JavaScript stealth patches (`navigator.webdriver = undefined`, etc.)
- Random delays between page loads and store visits
- Optional SSH SOCKS5 proxy routing

---

## Vehicle Type Detection

The scraper detects three vehicle conditions from the `li.entity-flag span.flag` elements on each listing and from regex matches on page text and HTML source:

| Type | Croatian label    | English alias                    |
| ---- | ----------------- | -------------------------------- |
| New  | `Novo vozilo`     | `new vehicle`                    |
| Used | `Rabljeno vozilo` | `used vehicle`, `polovno vozilo` |
| Test | `Testno vozilo`   | —                                |

All three counts are stored separately.
`total_vehicle_count = new + used + test`

---

## Active vs. Sold Tracking

Because njuskalo.hr only shows **live** ads, the scraper cannot directly see sold listings. Instead it tracks count changes between runs.

Every time a store is scraped a snapshot row is written to `store_snapshots`:

- `active_new / used / test / total` — ads visible on the page right now
- `delta_new / used / test / total` — difference vs. the previous run

A **negative delta** means that many ads disappeared since the last scrape (sold, expired, or removed).
A **positive delta** means new stock was listed.
On the **first run** for a store there is no previous snapshot, so all deltas are `0`.

### Example

| run | active_new | delta_new | interpretation                  |
| --- | ---------- | --------- | ------------------------------- |
| 1   | 12         | 0         | first scrape, no baseline       |
| 2   | 9          | −3        | 3 new-car listings removed/sold |
| 3   | 11         | +2        | 2 new cars re-stocked           |

### Querying the history

```sql
-- All snapshots for one store, newest first
SELECT scraped_at,
       active_new, active_used, active_test, active_total,
       delta_new, delta_used, delta_test, delta_total
FROM store_snapshots
WHERE url = 'https://www.njuskalo.hr/trgovina/some-store'
ORDER BY scraped_at DESC;

-- Stores with the most removals (sold) in new vehicles across all runs
SELECT url,
       SUM(CASE WHEN delta_new < 0 THEN ABS(delta_new) ELSE 0 END) AS total_sold_new
FROM store_snapshots
GROUP BY url
ORDER BY total_sold_new DESC
LIMIT 20;
```

You can run these queries directly against the SQLite file:

```bash
sqlite3 njuskalo.db
```

---

## Database

The scraper uses **SQLite** — a single file (`njuskalo.db` by default, path set via `DATABASE_PATH` in `.env`). No database server required. The file is created automatically on first run.

### `scraped_stores` — one row per store, updated on every scrape

| Column                | Type    | Description                          |
| --------------------- | ------- | ------------------------------------ |
| `id`                  | INTEGER | Auto-increment primary key           |
| `url`                 | TEXT    | Store URL (unique)                   |
| `results`             | TEXT    | Raw scraped data (JSON)              |
| `is_valid`            | INTEGER | 1 = URL was reachable                |
| `is_automoto`         | INTEGER | 1 = store has Auto Moto category     |
| `new_vehicle_count`   | INTEGER | Active new-vehicle ads (latest run)  |
| `used_vehicle_count`  | INTEGER | Active used-vehicle ads (latest run) |
| `test_vehicle_count`  | INTEGER | Active test-vehicle ads (latest run) |
| `total_vehicle_count` | INTEGER | Sum of all three types               |
| `created_at`          | TEXT    | First scrape (ISO 8601)              |
| `updated_at`          | TEXT    | Last scrape (ISO 8601)               |

### `store_snapshots` — one row per store per scrape run

| Column         | Type    | Description                                  |
| -------------- | ------- | -------------------------------------------- |
| `id`           | INTEGER | Auto-increment primary key                   |
| `url`          | TEXT    | Store URL                                    |
| `scraped_at`   | TEXT    | When this run happened (ISO 8601)            |
| `active_new`   | INTEGER | New-vehicle ads visible this run             |
| `active_used`  | INTEGER | Used-vehicle ads visible this run            |
| `active_test`  | INTEGER | Test-vehicle ads visible this run            |
| `active_total` | INTEGER | Total ads visible this run                   |
| `delta_new`    | INTEGER | Change vs. previous run (negative = removed) |
| `delta_used`   | INTEGER | Change vs. previous run                      |
| `delta_test`   | INTEGER | Change vs. previous run                      |
| `delta_total`  | INTEGER | Change vs. previous run                      |

Tables and indexes are created automatically on first run. Migrations are idempotent and safe to re-run on existing databases.

### Database management

```bash
python db_manager.py stats           # show store counts
python db_manager.py list-valid      # list valid stores
python db_manager.py list-invalid    # list invalid stores
python db_manager.py search --query "toyota"
python db_manager.py export          # dump to JSON
python db_manager.py migrate         # run pending migrations
```

---

## Exporting to Excel

```bash
# All valid stores
python export_db_to_excel.py

# Auto moto stores only
python export_db_to_excel.py --only-automoto

# Include stores marked invalid
python export_db_to_excel.py --include-invalid

# Custom filename
python export_db_to_excel.py --filename my_report.xlsx
```

Output goes to `datadump/`. The Excel file contains:

| Column group               | Columns                                                                       |
| -------------------------- | ----------------------------------------------------------------------------- |
| Store info                 | `id`, `vat`, `name`, `subname`, `address`, `url`, `is_automoto`, `updated_at` |
| Active counts (latest run) | `active_new`, `active_used`, `active_test`, `active_total`                    |
| Deltas vs. previous run    | `delta_new`, `delta_used`, `delta_test`, `delta_total`                        |
| Legacy convenience         | `new`, `used`, `test`, `total` (same values as `active_*`)                    |

Delta columns are `0` for stores that have only been scraped once (no prior baseline).

---

## SSH Tunnel Support

Tunnel mode routes Firefox traffic through an SSH SOCKS5 proxy to avoid IP-based rate limiting.

### tunnel_config.json format

```json
{
  "tunnels": {
    "my-server": {
      "ssh_host": "your.server.com",
      "ssh_port": 22,
      "ssh_user": "username",
      "ssh_key_path": "/home/user/njuskalohr/tunnel_key",
      "local_port": 1080
    }
  }
}
```

### Setup

```bash
# Install tunnel helper
./install_ssh_tunnel.sh

# Test Firefox + tunnel connectivity
python test_xvfb_firefox.py
python test_xvfb_firefox.py --skip-tunnel   # skip tunnel tests
python test_xvfb_firefox.py --verbose
```

See [TUNNEL_README.md](TUNNEL_README.md) for full tunnel setup details.

---

## Troubleshooting

### Firefox cannot open / display errors

The scraper uses the VNC display defined in `DISPLAY_NUM` (default `:3`). Verify it is running:

```bash
DISPLAY=:3 xdpyinfo | head -5
```

If that fails, the Xvfb/VNC process on the server needs to be restarted — this is outside the scope of the scraper. Once the display is up, re-run:

```bash
./run.sh --max-stores 3 --verbose
```

### GeckoDriver not found

```bash
geckodriver --version
which geckodriver
```

GeckoDriver must be on `PATH` (e.g. `/usr/local/bin/geckodriver`). Reinstall following step 2 of the installation section.

### Database errors

The SQLite file is created automatically. If you see permission errors, check that the process has write access to the directory containing `DATABASE_PATH`:

```bash
ls -l njuskalo.db
```

### Low vehicle counts or zero results

- The scraper caps per-page counts at 100 to avoid false positives from regex over-matching
- Try `--verbose` to see per-page detection logs
- Run `--mode basic` to confirm the store page is reachable at all

### Tunnel not connecting

```bash
# Check SSH key permissions
chmod 600 /home/user/njuskalohr/tunnel_key

# Test connectivity manually
ssh -i tunnel_key -D 1080 username@your.server.com -N

# Run without tunnels to isolate the issue
./run.sh --no-tunnels
```
