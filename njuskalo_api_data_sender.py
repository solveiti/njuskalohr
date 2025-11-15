#!/usr/bin/env python3
"""
Dober Avto API Client - Database Version
Converts dealership statistics from Njuskalo database and sends to Dober Avto API.

Usage:
    python njuskalo_api_data_sender.py --scraping-date 2025-11-08
    python njuskalo_api_data_sender.py --scraping-date 2025-11-08 --min-vehicles 5
    python njuskalo_api_data_sender.py --help
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests
from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
import logging

# Load environment variables
load_dotenv()

# Initialize Sentry
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0")),
        integrations=[LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)],
    )

# Import database class
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import NjuskaloDatabase


class DoberApiClient:
    """Client for interacting with Dober Avto API"""

    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()

        self.base_url = os.getenv('DOBER_API_BASE_URL', 'https://www.doberavto.si/internal-api/v1/')
        self.api_key = os.getenv('DOBER_API_KEY')
        self.timeout = float(os.getenv('DOBER_API_TIMEOUT', '5000')) / 1000  # Convert ms to seconds

        if not self.api_key:
            raise ValueError("DOBER_API_KEY not found in environment variables")

        # Ensure base_url ends with /
        if not self.base_url.endswith('/'):
            self.base_url += '/'

        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-Api-Key': self.api_key
        })

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make HTTP request to API"""
        url = f"{self.base_url}{endpoint}"

        try:
            if method.upper() == 'GET':
                response = self.session.get(url, timeout=self.timeout)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, timeout=self.timeout)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, timeout=self.timeout)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            print(f"{method.upper()} {endpoint}")
            if data:
                print(f"Request data: {json.dumps(data, indent=2)}")
            print(f"Response: {response.text}")
            print()

            response.raise_for_status()

            try:
                return {
                    'status': response.status_code,
                    'data': response.json()
                }
            except json.JSONDecodeError:
                return {
                    'status': response.status_code,
                    'data': response.text
                }

        except requests.exceptions.RequestException as e:
            return {'error': str(e)}

    def get(self, endpoint: str) -> Dict:
        """Make GET request"""
        return self._make_request('GET', endpoint)

    def post(self, endpoint: str, data: Dict) -> Dict:
        """Make POST request"""
        return self._make_request('POST', endpoint, data)

    def put(self, endpoint: str, data: Dict) -> Dict:
        """Make PUT request"""
        return self._make_request('PUT', endpoint, data)

    def delete(self, endpoint: str) -> Dict:
        """Make DELETE request"""
        return self._make_request('DELETE', endpoint)


class DealershipProcessor:
    """Process dealership data from Njuskalo database"""

    def __init__(self, api_client: DoberApiClient):
        self.api = api_client

    def get_dealerships_per_tin(self, dealerships_list: List[Dict]) -> Dict[str, List[Dict]]:
        """Group dealerships by TIN (tax identification number)"""
        result = {}
        for dealership in (dealerships_list or []):
            if not dealership.get('tin'):
                continue

            # Remove spaces from TIN
            tin = dealership['tin'].replace(' ', '')
            if tin not in result:
                result[tin] = []
            result[tin].append(dealership)

        return result

    def match_external_dealership(self, njuskalo_data: Dict, options: List[Dict]) -> Optional[Dict]:
        """Find matching external dealership by external ID"""
        for option in (options or []):
            if option.get('externalId') == f"njuskalo-{njuskalo_data['id']}":
                return option
        return None

    def match_native_dealership(self, njuskalo_data: Dict, options: List[Dict]) -> Optional[Dict]:
        """Find best matching native dealership by address and name scoring"""
        if not options:
            return None

        if len(options) == 1:
            return options[0]

        # Try match by address and name
        src_addr = (njuskalo_data.get('address') or '').lower()
        src_name = (njuskalo_data.get('name') or '').lower()
        search_text = f"{src_addr} {src_name}".lower()

        score_per_match = []

        for item in options:
            score = 0

            # Address town match
            if item.get('addressTown') and item['addressTown'].lower() in search_text:
                score += 100

            # Address street match
            if item.get('addressStreet') and item['addressStreet'].lower() in search_text:
                score += 50

            # Company name word matches
            company_words = (item.get('companyName') or '').split()
            for word in filter(None, company_words):
                if len(word) > 2 and word.lower() in search_text:
                    score += 5

            # Public name word matches
            public_words = (item.get('publicName') or '').split()
            for word in filter(None, public_words):
                if len(word) > 2 and word.lower() in search_text:
                    score += 3

            # Njuskalo name matches company name
            if src_name and item.get('companyName'):
                common_words = set(src_name.split()) & set(item['companyName'].lower().split())
                score += len(common_words) * 10

            # Penalize service companies unless explicitly matching
            if score and 'servis' in (item.get('companyName') or '').lower():
                if 'servis' not in search_text:
                    score -= 5

            score_per_match.append(score)

        # Find best match
        best_match = None
        max_score = 0

        for i, score in enumerate(score_per_match):
            if score > max_score:
                max_score = score
                best_match = options[i]

        return best_match

    def get_dealerships_from_database(self, scraping_date: str, min_vehicles: int = 0) -> List[Dict]:
        """Extract dealership data from Njuskalo database"""
        rows = []

        try:
            with NjuskaloDatabase() as db:
                # Get all auto moto stores from database
                stores = db.get_auto_moto_stores()

                print(f"Found {len(stores)} auto moto stores in database")

                for store in stores:
                    # Filter by scraping date if specified
                    if scraping_date:
                        store_date = store.get('updated_at') or store.get('created_at')
                        if store_date:
                            store_date_str = store_date.strftime('%Y-%m-%d')
                            if store_date_str != scraping_date:
                                continue

                    # Get results JSON data
                    results = store.get('results', {}) or {}

                    # Calculate total vehicle count from database or results
                    new_count = store.get('new_vehicle_count') or 0
                    used_count = store.get('used_vehicle_count') or 0
                    total_count = store.get('total_vehicle_count') or 0

                    # If database counts are 0 or None, try to get from results
                    if not total_count and results:
                        total_count = results.get('total_vehicle_count', 0)
                        new_count = results.get('new_vehicle_count', 0)
                        used_count = results.get('used_vehicle_count', 0)

                    # If still no vehicle count, use ads_count as fallback
                    if not total_count:
                        total_count = results.get('ads_count', 0) or 0
                        # Estimate new/used split (roughly 30% new, 70% used)
                        new_count = int(total_count * 0.3)
                        used_count = total_count - new_count

                    # Skip stores with fewer vehicles than minimum
                    if total_count < min_vehicles:
                        continue

                    # Extract TIN from results or try to derive from address
                    tin = self.extract_tin_from_store_data(results, store)

                    # Extract store ID from URL
                    store_id = self.extract_store_id_from_url(store.get('url', ''))

                    # Clean up data values
                    def clean_data(value):
                        if isinstance(value, str):
                            if value.startswith("exception") or not value.strip():
                                return ""
                        return value or ""

                    rows.append({
                        'id': store_id,
                        'tin': tin,
                        'name': clean_data(results.get('name') or store.get('url', '').split('/')[-1]),
                        'subname': clean_data(results.get('subname', '')),
                        'address': clean_data(results.get('address', '')),
                        'total': total_count,
                        'new': new_count,
                        'used': used_count,
                        'test': 0,  # Test vehicles not tracked separately in current schema
                        'url': store.get('url', ''),
                        'scraped_at': store.get('updated_at') or store.get('created_at')
                    })

                print(f"Processed {len(rows)} dealerships with >= {min_vehicles} vehicles")
                return rows

        except Exception as e:
            print(f"Error extracting dealerships from database: {e}")
            return []

    def extract_tin_from_store_data(self, results: Dict, store: Dict) -> str:
        """Extract TIN/VAT number from store data"""
        # Try to get TIN from results JSON
        tin = results.get('vat') or results.get('tin') or results.get('oib')

        if tin:
            return str(tin).replace(' ', '').replace('-', '')

        # If no TIN found, try to extract from address or name using Croatian TIN patterns
        address = results.get('address', '') or ''
        name = results.get('name', '') or ''

        # Croatian TIN (OIB) is 11 digits
        text_to_search = f"{address} {name}"
        oib_match = re.search(r'\b\d{11}\b', text_to_search)
        if oib_match:
            return oib_match.group(0)

        # Company registration number patterns
        reg_match = re.search(r'\b\d{8,10}\b', text_to_search)
        if reg_match:
            return reg_match.group(0)

        return ""  # No TIN found

    def extract_store_id_from_url(self, url: str) -> str:
        """Extract store ID from Njuskalo store URL"""
        # Try to extract ID from URL patterns like /trgovina/12345/store-name
        match = re.search(r'/trgovina/(\d+)', url)
        if match:
            return match.group(1)

        # Fallback: use hash of URL
        import hashlib
        return str(abs(hash(url)) % 1000000)  # 6-digit pseudo-ID

    def create_external_dealership(self, data: Dict, native: Optional[Dict] = None) -> Optional[str]:
        """Create external dealership record"""
        # Extract city from address for better organization
        address = data.get('address', '')
        city = ''
        if address:
            # Try to extract Croatian city from address
            # Croatian addresses usually end with postal code + city
            city_match = re.search(r'\d{5}\s+([A-ZČĆŽŠĐ][a-zčćžšđ\s]+)', address)
            if city_match:
                city = city_match.group(1).strip()
            else:
                # Fallback: take last word that looks like a city
                words = address.split()
                for word in reversed(words):
                    if len(word) > 2 and word[0].isupper():
                        city = word
                        break

        payload = {
            'externalId': f"njuskalo-{data['id']}",
            'nativeDealership': {'code': native['code']} if native else None,
            'name': data['name'] or f"Njuskalo Store {data['id']}",
            'tin': data['tin'],
            'address_street': address,
            'address_town': city,
        }

        result = self.api.post('external-statistics/dealers', payload)

        if 'error' in result:
            print(f"Error creating external dealership: {result['error']}")
            return None

        return result.get('data', {}).get('id')

    def send_dealership_statistics(self, data: List[Dict], scraping_date: str) -> Dict:
        """Send dealership statistics to API"""
        payload = {
            'collectedOn': f"{scraping_date}T12:00:00Z",
            'data': data,
        }

        result = self.api.post('external-statistics/dealership-statistics', payload)
        print("Statistics sent:", result)
        return result

    def process_dealerships(self, scraping_date: str, min_vehicles: int = 0) -> None:
        """Main processing function"""
        print(f"Processing dealerships from database for date: {scraping_date}")
        print(f"Minimum vehicles threshold: {min_vehicles}")

        # Get native dealerships from API
        native_response = self.api.get('external-statistics/native-dealers')
        native_dealerships = self.get_dealerships_per_tin(
            native_response.get('data', {}).get('dealerships', []) if 'error' not in native_response else []
        )

        # Get external dealerships from API
        external_response = self.api.get('external-statistics/dealers')
        external_dealerships = self.get_dealerships_per_tin(
            external_response.get('data', {}).get('dealerships', []) if 'error' not in external_response else []
        )

        # Get Njuskalo dealerships from database
        njuskalo_dealerships = self.get_dealerships_per_tin(
            self.get_dealerships_from_database(scraping_date, min_vehicles)
        )

        print(f"Found {len(njuskalo_dealerships)} unique TINs in database")

        statistics_data = []
        processed_count = 0
        created_count = 0

        for tin, dealerships in njuskalo_dealerships.items():
            for stat in dealerships:
                dealership_id = None

                # Try to match existing external dealership
                ext_dealership = self.match_external_dealership(stat, external_dealerships.get(tin, []))
                if ext_dealership:
                    dealership_id = ext_dealership['id']
                    print(f"Matched existing external dealership: {stat['name']} (TIN: {tin})")

                # If not found, create new external dealership
                if not dealership_id:
                    native_for_new_external = self.match_native_dealership(stat, native_dealerships.get(tin, []))
                    dealership_id = self.create_external_dealership(stat, native_for_new_external)
                    if dealership_id:
                        created_count += 1
                        print(f"Created new external dealership: {stat['name']} (TIN: {tin})")

                if dealership_id:
                    statistics_data.append({
                        'dealershipId': dealership_id,
                        'postingsTotal': stat.get('total', 0),
                        'postingsSourceNew': stat.get('new', 0),
                        'postingsSourceUsed': stat.get('used', 0),
                        'postingsSourceTest': stat.get('test', 0)
                    })
                    processed_count += 1
                else:
                    print(f"Failed to process dealership: {stat['name']} (TIN: {tin})")

        # Send statistics if we have data
        if statistics_data:
            result = self.send_dealership_statistics(statistics_data, scraping_date)
            print(f"\n📊 Processing Summary:")
            print(f"  Processed: {processed_count} dealerships")
            print(f"  Created new: {created_count} dealerships")
            print(f"  Sent statistics for: {len(statistics_data)} dealerships")
            print(f"  Total vehicles: {sum(stat['postingsTotal'] for stat in statistics_data)}")
        else:
            print("No statistics data to send")


def main():
    parser = argparse.ArgumentParser(
        description='Send Njuskalo dealership statistics to Dober Avto API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --scraping-date 2025-11-08
  %(prog)s --scraping-date 2025-11-08 --min-vehicles 5
  %(prog)s --scraping-date 2025-11-08 --env-file /path/to/.env
        """
    )

    parser.add_argument(
        '--scraping-date',
        required=False,
        default=datetime.now().strftime('%Y-%m-%d'),
        help='Date of scraping in YYYY-MM-DD format (default: today)'
    )

    parser.add_argument(
        '--min-vehicles',
        type=int,
        default=1,
        help='Minimum number of vehicles required to include dealership (default: 1)'
    )

    parser.add_argument(
        '--env-file',
        type=Path,
        default=Path(__file__).parent / '.env',
        help='Path to .env file (default: .env in script directory)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be sent without actually sending to API'
    )

    args = parser.parse_args()

    # Load environment from specified file
    if args.env_file.exists():
        load_dotenv(args.env_file)
        if args.verbose:
            print(f"Loaded environment from: {args.env_file}")
    else:
        print(f"Warning: Environment file not found: {args.env_file}")

    try:
        # Initialize API client
        if args.dry_run:
            print("🔍 DRY RUN MODE - No data will be sent to API")

        api_client = DoberApiClient()

        # Initialize processor
        processor = DealershipProcessor(api_client)

        # Process dealerships
        if args.dry_run:
            # In dry run mode, just show what we would process
            dealerships = processor.get_dealerships_from_database(args.scraping_date, args.min_vehicles)
            print(f"\n📋 Would process {len(dealerships)} dealerships:")
            for d in dealerships[:10]:  # Show first 10
                print(f"  - {d['name'][:30]:30} | TIN: {d['tin'][:15]:15} | Vehicles: {d['total']:3}")
            if len(dealerships) > 10:
                print(f"  ... and {len(dealerships) - 10} more dealerships")
        else:
            processor.process_dealerships(args.scraping_date, args.min_vehicles)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()