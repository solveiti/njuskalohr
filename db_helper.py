"""
Simple database helper for Njuskalo HR system.
Basic functions to query existing database tables.
"""

import os
import json
import pymysql
from typing import Dict, List, Optional, Any
import logging
from dotenv import load_dotenv

from models import (
    User, UserToken, UserLogin, File, FileGroup, Menu, MenuItem,
    Page, Block, BlockGroup, PageBlock, PageBlockGroup, PageBlockPhoto,
    AdItem, AdPhoto, AvtoAdItem, AvtoAdPhoto, ScrapedStore,
    parse_json_field
)

# Load environment variables
load_dotenv()


class SimpleDatabase:
    """Simple database connection helper"""

    def __init__(self):
        self.connection_params = {
            'host': os.getenv('DATABASE_HOST', 'localhost'),
            'port': int(os.getenv('DATABASE_PORT', '3306')),
            'database': os.getenv('DATABASE_NAME', 'njuskalohr'),
            'user': os.getenv('DATABASE_USER'),
            'password': os.getenv('DATABASE_PASSWORD'),
            'charset': 'utf8mb4',
            'autocommit': False
        }
        self.connection = None
        self.logger = logging.getLogger(__name__)

    def connect(self):
        """Establish database connection"""
        try:
            self.connection = pymysql.connect(**self.connection_params)
            self.logger.info("Connected to MySQL database")
        except pymysql.Error as e:
            self.logger.error(f"Error connecting to database: {e}")
            raise

    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

    def _format_uuid(self, hex_uuid: str) -> str:
        """Format hex UUID to standard UUID string"""
        if not hex_uuid or len(hex_uuid) != 32:
            return hex_uuid
        return f"{hex_uuid[:8]}-{hex_uuid[8:12]}-{hex_uuid[12:16]}-{hex_uuid[16:20]}-{hex_uuid[20:]}"

    def _parse_row(self, row: Dict, model_class) -> Dict:
        """Parse database row and format UUIDs and JSON fields"""
        if not row:
            return None

        # Format UUIDs
        for field in ['uuid', 'userUuid', 'tokenUuid', 'parent', 'menu', 'photo',
                      'pageBlockGroup', 'blockGroup', 'user', 'aditem', 'logo']:
            if field in row and row[field]:
                row[field] = self._format_uuid(row[field])

        # Parse JSON fields
        json_fields = ['profile', 'company', 'avtonet', 'njuskalo', 'content', 'variants', 'results']
        for field in json_fields:
            if field in row:
                row[field] = parse_json_field(row[field])

        return row

    # User queries
    def get_users(self, limit: int = 100) -> List[Dict]:
        """Get all users"""
        try:
            sql = """
            SELECT id, HEX(uuid) as uuid, username, email, newemail, `group`, photo,
                   mainUser, consent, deleted, profile, company, HEX(logo) as logo,
                   avtonet, njuskalo
            FROM users
            WHERE deleted IS NULL OR deleted = 0
            ORDER BY username
            LIMIT %s
            """

            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, (limit,))
                results = cursor.fetchall()
                return [self._parse_row(row, User) for row in results]

        except pymysql.Error as e:
            self.logger.error(f"Error getting users: {e}")
            return []

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        try:
            sql = """
            SELECT id, HEX(uuid) as uuid, username, email, newemail, `group`, photo,
                   mainUser, consent, deleted, profile, company, HEX(logo) as logo,
                   avtonet, njuskalo
            FROM users
            WHERE username = %s AND (deleted IS NULL OR deleted = 0)
            """

            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, (username,))
                result = cursor.fetchone()
                return self._parse_row(result, User) if result else None

        except pymysql.Error as e:
            self.logger.error(f"Error getting user by username: {e}")
            return None

    def get_user_by_uuid(self, user_uuid: str) -> Optional[Dict]:
        """Get user by UUID"""
        try:
            sql = """
            SELECT id, HEX(uuid) as uuid, username, email, newemail, `group`, photo,
                   mainUser, consent, deleted, profile, company, HEX(logo) as logo,
                   avtonet, njuskalo
            FROM users
            WHERE uuid = UNHEX(REPLACE(%s, '-', '')) AND (deleted IS NULL OR deleted = 0)
            """

            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, (user_uuid,))
                result = cursor.fetchone()
                return self._parse_row(result, User) if result else None

        except pymysql.Error as e:
            self.logger.error(f"Error getting user by UUID: {e}")
            return None

    # Ad queries
    def get_ad_items(self, user_uuid: str = None, limit: int = 100) -> List[Dict]:
        """Get ad items, optionally filtered by user"""
        try:
            if user_uuid:
                sql = """
                SELECT id, HEX(uuid) as uuid, HEX(user) as user, title, created, updated,
                       status, content, adCode, doberAvtoCode, publishDoberAvto, publishAvtoNet
                FROM aditem
                WHERE user = UNHEX(REPLACE(%s, '-', ''))
                ORDER BY created DESC
                LIMIT %s
                """
                params = (user_uuid, limit)
            else:
                sql = """
                SELECT id, HEX(uuid) as uuid, HEX(user) as user, title, created, updated,
                       status, content, adCode, doberAvtoCode, publishDoberAvto, publishAvtoNet
                FROM aditem
                ORDER BY created DESC
                LIMIT %s
                """
                params = (limit,)

            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, params)
                results = cursor.fetchall()
                return [self._parse_row(row, AdItem) for row in results]

        except pymysql.Error as e:
            self.logger.error(f"Error getting ad items: {e}")
            return []

    def get_ad_photos(self, ad_uuid: str) -> List[Dict]:
        """Get photos for an ad item"""
        try:
            sql = """
            SELECT id, HEX(uuid) as uuid, HEX(aditem) as aditem, orderindex,
                   HEX(photo) as photo, HEX(extUuid) as extUuid
            FROM adPhotos
            WHERE aditem = UNHEX(REPLACE(%s, '-', ''))
            ORDER BY orderindex
            """

            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, (ad_uuid,))
                results = cursor.fetchall()
                return [self._parse_row(row, AdPhoto) for row in results]

        except pymysql.Error as e:
            self.logger.error(f"Error getting ad photos: {e}")
            return []

    def get_ad_by_uuid(self, ad_uuid: str) -> Optional[Dict]:
        """Get a single ad by UUID"""
        try:
            sql = """
            SELECT id, HEX(uuid) as uuid, HEX(user) as user, title, created, updated,
                   status, content, adCode, doberAvtoCode, publishDoberAvto, publishAvtoNet, publishNjuskalo
            FROM aditem
            WHERE uuid = UNHEX(REPLACE(%s, '-', ''))
            LIMIT 1
            """

            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, (ad_uuid,))
                result = cursor.fetchone()
                if result:
                    return self._parse_row(result, AdItem)
                return None

        except pymysql.Error as e:
            self.logger.error(f"Error getting ad by UUID: {e}")
            return None

    def get_published_ads_by_user(self, user_uuid: str) -> List[Dict]:
        """Get published ads for a specific user that have publishNjuskalo enabled"""
        try:
            sql = """
            SELECT id, HEX(uuid) as uuid, HEX(user) as user, title, created, updated,
                   status, content, adCode, doberAvtoCode, publishDoberAvto, publishAvtoNet, publishNjuskalo
            FROM aditem
            WHERE user = UNHEX(REPLACE(%s, '-', ''))
              AND status = 'published'
              AND publishNjuskalo = 1
            ORDER BY created DESC
            """

            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, (user_uuid,))
                results = cursor.fetchall()
                return [self._parse_row(row, AdItem) for row in results]

        except pymysql.Error as e:
            self.logger.error(f"Error getting published ads by user: {e}")
            return []

    # Page queries
    def get_pages(self, language: str = 'en', limit: int = 100) -> List[Dict]:
        """Get pages by language"""
        try:
            sql = """
            SELECT id, HEX(uuid) as uuid, HEX(parent) as parent, slug, target, template,
                   title, intro, HEX(photo) as photo, HEX(pageBlockGroup) as pageBlockGroup,
                   HEX(blockGroup) as blockGroup, htmlTitle, htmlDescription,
                   language, updated, deleted
            FROM pages
            WHERE language = %s AND (deleted IS NULL OR deleted = 0)
            ORDER BY title
            LIMIT %s
            """

            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, (language, limit))
                results = cursor.fetchall()
                return [self._parse_row(row, Page) for row in results]

        except pymysql.Error as e:
            self.logger.error(f"Error getting pages: {e}")
            return []

    def get_page_by_slug(self, slug: str, language: str = 'en') -> Optional[Dict]:
        """Get page by slug"""
        try:
            sql = """
            SELECT id, HEX(uuid) as uuid, HEX(parent) as parent, slug, target, template,
                   title, intro, HEX(photo) as photo, HEX(pageBlockGroup) as pageBlockGroup,
                   HEX(blockGroup) as blockGroup, htmlTitle, htmlDescription,
                   language, updated, deleted
            FROM pages
            WHERE slug = %s AND language = %s AND (deleted IS NULL OR deleted = 0)
            """

            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, (slug, language))
                result = cursor.fetchone()
                return self._parse_row(result, Page) if result else None

        except pymysql.Error as e:
            self.logger.error(f"Error getting page by slug: {e}")
            return None

    # Menu queries
    def get_menus(self, limit: int = 50) -> List[Dict]:
        """Get all menus"""
        try:
            sql = """
            SELECT id, HEX(uuid) as uuid, HEX(parent) as parent, orderindex, title, slug
            FROM menus
            ORDER BY orderindex, title
            LIMIT %s
            """

            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, (limit,))
                results = cursor.fetchall()
                return [self._parse_row(row, Menu) for row in results]

        except pymysql.Error as e:
            self.logger.error(f"Error getting menus: {e}")
            return []

    def get_menu_items(self, menu_uuid: str, language: str = 'en') -> List[Dict]:
        """Get menu items for a specific menu"""
        try:
            sql = """
            SELECT id, HEX(uuid) as uuid, HEX(menu) as menu, HEX(parent) as parent,
                   orderindex, title, target, HEX(photo) as photo, language
            FROM menuitems
            WHERE menu = UNHEX(REPLACE(%s, '-', '')) AND language = %s
            ORDER BY orderindex, title
            """

            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, (menu_uuid, language))
                results = cursor.fetchall()
                return [self._parse_row(row, MenuItem) for row in results]

        except pymysql.Error as e:
            self.logger.error(f"Error getting menu items: {e}")
            return []

    # File queries
    def get_files(self, limit: int = 100) -> List[Dict]:
        """Get files"""
        try:
            sql = """
            SELECT id, HEX(uuid) as uuid, HEX(parent) as parent, filename, size, uploaded,
                   type, description, mimetype, variants, deleted
            FROM files
            WHERE deleted IS NULL OR deleted = 0
            ORDER BY uploaded DESC
            LIMIT %s
            """

            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, (limit,))
                results = cursor.fetchall()
                return [self._parse_row(row, File) for row in results]

        except pymysql.Error as e:
            self.logger.error(f"Error getting files: {e}")
            return []

    def get_file_by_uuid(self, file_uuid: str) -> Optional[Dict]:
        """Get file by UUID"""
        try:
            sql = """
            SELECT id, HEX(uuid) as uuid, HEX(parent) as parent, filename, size, uploaded,
                   type, description, mimetype, variants, deleted
            FROM files
            WHERE uuid = UNHEX(REPLACE(%s, '-', '')) AND (deleted IS NULL OR deleted = 0)
            """

            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, (file_uuid,))
                result = cursor.fetchone()
                return self._parse_row(result, File) if result else None

        except pymysql.Error as e:
            self.logger.error(f"Error getting file by UUID: {e}")
            return None

    # Statistics
    def get_table_counts(self) -> Dict[str, int]:
        """Get count of records in each table"""
        tables = [
            'users', 'userTokens', 'userLogins', 'files', 'fileGroups',
            'menus', 'menuitems', 'pages', 'blocks', 'blockGroups',
            'pageBlocks', 'pageBlockGroups', 'pageBlockPhotos',
            'aditem', 'adPhotos', 'avtoaditem', 'avtoadPhotos', 'scraped_stores'
        ]

        counts = {}
        try:
            with self.connection.cursor() as cursor:
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        counts[table] = cursor.fetchone()[0]
                    except pymysql.Error:
                        counts[table] = 0

            return counts

        except pymysql.Error as e:
            self.logger.error(f"Error getting table counts: {e}")
            return {table: 0 for table in tables}

    # Update methods
    def update_ad_njuskalo_code(self, ad_uuid: str, njuskalo_code: str) -> bool:
        """Update the doberAvtoCode field for an ad item"""
        try:
            import uuid as uuid_lib

            # Convert UUID string to binary
            try:
                uuid_obj = uuid_lib.UUID(ad_uuid)
                uuid_binary = uuid_obj.bytes
            except ValueError:
                self.logger.error(f"Invalid UUID format: {ad_uuid}")
                return False

            with self.connection.cursor() as cursor:
                sql = """
                    UPDATE aditem
                    SET doberAvtoCode = %s
                    WHERE uuid = %s
                """
                cursor.execute(sql, (njuskalo_code, uuid_binary))
                self.connection.commit()

                if cursor.rowcount > 0:
                    self.logger.info(f"✅ Updated doberAvtoCode for ad {ad_uuid}: {njuskalo_code}")
                    return True
                else:
                    # Try with string UUID
                    sql = """
                        UPDATE aditem
                        SET doberAvtoCode = %s
                        WHERE HEX(uuid) = %s
                    """
                    cursor.execute(sql, (njuskalo_code, ad_uuid.replace('-', '').upper()))
                    self.connection.commit()

                    if cursor.rowcount > 0:
                        self.logger.info(f"✅ Updated doberAvtoCode for ad {ad_uuid}: {njuskalo_code}")
                        return True
                    else:
                        self.logger.warning(f"No ad found with UUID: {ad_uuid}")
                        return False

        except pymysql.Error as e:
            self.logger.error(f"Error updating ad njuskalo code: {e}")
            self.connection.rollback()
            return False

    # Raw query method for custom queries
    def execute_query(self, sql: str, params: tuple = None) -> List[Dict]:
        """Execute a custom SQL query"""
        try:
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, params or ())
                results = cursor.fetchall()
                return [dict(row) for row in results]

        except pymysql.Error as e:
            self.logger.error(f"Error executing query: {e}")
            return []