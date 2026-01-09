#!/usr/bin/env python3
"""
Add processing_metadata table to ohlc_data.db

This table tracks incremental processing progress for all pipeline steps.
CRITICAL for efficient daily updates - without this, we'd reprocess everything daily!

This migration is SAFE to run multiple times (uses IF NOT EXISTS).
"""

import sqlite3
from datetime import datetime

DB_PATH = 'data/ohlc_data.db'

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 80)
    print("MIGRATION: Add processing_metadata table to ohlc_data.db")
    print("=" * 80)
    print()

    # Check if table already exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='processing_metadata'
    """)

    if cursor.fetchone():
        print("[SKIP] processing_metadata table already exists")
        print("       Skipping table creation...")
    else:
        print("Creating processing_metadata table...")

        cursor.execute("""
            CREATE TABLE processing_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                process_type TEXT NOT NULL,
                last_processed_time TEXT,
                records_processed INTEGER,
                status TEXT NOT NULL,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,

                UNIQUE(symbol, process_type)
            )
        """)

        print("[OK] Table created")

    # Check if index exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index' AND name='idx_metadata_symbol_type'
    """)

    if cursor.fetchone():
        print("[SKIP] Index idx_metadata_symbol_type already exists")
    else:
        print("Creating index idx_metadata_symbol_type...")

        cursor.execute("""
            CREATE INDEX idx_metadata_symbol_type
            ON processing_metadata(symbol, process_type)
        """)

        print("[OK] Index created")

    conn.commit()

    # Verify
    print()
    print("Verification:")
    print("-" * 80)

    cursor.execute("PRAGMA table_info(processing_metadata)")
    columns = cursor.fetchall()
    print(f"Columns: {len(columns)}")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")

    cursor.execute("""
        SELECT COUNT(*) FROM sqlite_master
        WHERE type='index' AND tbl_name='processing_metadata'
    """)
    index_count = cursor.fetchone()[0]
    print(f"Indexes: {index_count}")

    print()
    print("=" * 80)
    print("[SUCCESS] Migration complete!")
    print("=" * 80)

    conn.close()

if __name__ == '__main__':
    migrate()
