#!/usr/bin/env python3
"""
Migration script to add processing_metadata table to yearly_monthly.db.

This table tracks the last processed timestamp for each processing step
to enable incremental data loading and processing.

Usage:
    python migrate_add_processing_metadata.py
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = 'data/yearly_monthly.db'

def migrate_database():
    """Add processing_metadata table and session tracking columns."""

    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found: {DB_PATH}")
        print("Run create_yearly_monthly_db.py first to create the database.")
        return False

    print(f"Migrating database: {DB_PATH}")
    print("=" * 80)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    try:
        # Check if processing_metadata table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='processing_metadata'
        """)

        if cursor.fetchone():
            print("[INFO] processing_metadata table already exists. Skipping table creation.")
        else:
            # Create processing_metadata table
            print("[1/4] Creating processing_metadata table...")
            cursor.execute("""
                CREATE TABLE processing_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    process_type TEXT NOT NULL,
                    last_processed_time TEXT,
                    last_processed_candle_id INTEGER,
                    records_processed INTEGER,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,

                    UNIQUE(symbol, process_type)
                );
            """)

            cursor.execute("""
                CREATE INDEX idx_metadata_symbol_type
                ON processing_metadata(symbol, process_type);
            """)

            print("   [OK] processing_metadata table created")

        # Check if session tracking columns exist
        cursor.execute("PRAGMA table_info(sessions)")
        columns = {col[1] for col in cursor.fetchall()}

        # Add needs_recalc column if it doesn't exist
        if 'needs_recalc' not in columns:
            print("[2/4] Adding needs_recalc column to sessions...")
            cursor.execute("""
                ALTER TABLE sessions ADD COLUMN needs_recalc INTEGER DEFAULT 0
            """)
            print("   [OK] needs_recalc column added")
        else:
            print("[2/4] needs_recalc column already exists. Skipping.")

        # Add last_recalc_time column if it doesn't exist
        if 'last_recalc_time' not in columns:
            print("[3/4] Adding last_recalc_time column to sessions...")
            cursor.execute("""
                ALTER TABLE sessions ADD COLUMN last_recalc_time TEXT
            """)
            print("   [OK] last_recalc_time column added")
        else:
            print("[3/4] last_recalc_time column already exists. Skipping.")

        # Add last_poi_check_time column if it doesn't exist
        if 'last_poi_check_time' not in columns:
            print("[4/4] Adding last_poi_check_time column to sessions...")
            cursor.execute("""
                ALTER TABLE sessions ADD COLUMN last_poi_check_time TEXT
            """)
            print("   [OK] last_poi_check_time column added")
        else:
            print("[4/4] last_poi_check_time column already exists. Skipping.")

        # Commit changes
        conn.commit()

        print("\n" + "=" * 80)
        print("[OK] Migration completed successfully!")
        print("=" * 80)

        # Show new table structure
        print("\nprocessing_metadata table schema:")
        cursor.execute("PRAGMA table_info(processing_metadata)")
        for col in cursor.fetchall():
            print(f"  {col[1]}: {col[2]}")

        print("\nsessions table new columns:")
        cursor.execute("PRAGMA table_info(sessions)")
        for col in cursor.fetchall():
            if col[1] in ['needs_recalc', 'last_recalc_time', 'last_poi_check_time']:
                print(f"  {col[1]}: {col[2]}")

        return True

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def verify_migration():
    """Verify that migration was successful."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)

    # Check tables
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table'
        ORDER BY name
    """)
    tables = [row[0] for row in cursor.fetchall()]

    print(f"Total tables: {len(tables)}")
    print(f"processing_metadata exists: {'processing_metadata' in tables}")

    # Check indexes
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index' AND name='idx_metadata_symbol_type'
    """)
    has_index = cursor.fetchone() is not None
    print(f"idx_metadata_symbol_type exists: {has_index}")

    # Check session columns
    cursor.execute("PRAGMA table_info(sessions)")
    columns = {col[1] for col in cursor.fetchall()}
    print(f"needs_recalc column exists: {'needs_recalc' in columns}")
    print(f"last_recalc_time column exists: {'last_recalc_time' in columns}")
    print(f"last_poi_check_time column exists: {'last_poi_check_time' in columns}")

    conn.close()
    print("=" * 80)


if __name__ == '__main__':
    success = migrate_database()
    if success:
        verify_migration()
        print("\n[OK] Database is ready for incremental processing!")
    else:
        print("\n[ERROR] Migration failed. Please check errors above.")
