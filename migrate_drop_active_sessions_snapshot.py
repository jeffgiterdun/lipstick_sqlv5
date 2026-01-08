#!/usr/bin/env python3
"""
Migration: Drop active_sessions_snapshot column from swings table

This column was redundant - session context can be reconstructed
from the sessions table anytime using swing_time. The nearest_poi_event_id
already links to the most relevant session.

This migration removes the column to reduce storage and simplify the schema.
"""

import sqlite3

DB_PATH = 'data/ohlc_data.db'


def migrate():
    """Drop active_sessions_snapshot column from swings table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("Dropping active_sessions_snapshot column from swings table...")
        print()
        print("Note: SQLite doesn't support DROP COLUMN directly.")
        print("Will recreate table without the column...")
        print()

        # Step 1: Create new table without active_sessions_snapshot
        cursor.execute("""
            CREATE TABLE swings_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                swing_time TEXT NOT NULL,
                swing_price REAL NOT NULL,
                swing_type TEXT NOT NULL,
                swing_class INTEGER NOT NULL,

                -- Movement context
                prior_opposite_swing_id INTEGER,
                points_from_prior REAL,
                candles_from_prior INTEGER,

                -- POI linkage
                nearest_poi_event_id INTEGER,
                candles_from_poi_event INTEGER,

                created_at TEXT NOT NULL,
                FOREIGN KEY (prior_opposite_swing_id) REFERENCES swings(id),
                FOREIGN KEY (nearest_poi_event_id) REFERENCES poi_events(id)
            )
        """)
        print("[OK] Created new table schema")

        # Step 2: Copy data (excluding active_sessions_snapshot)
        cursor.execute("""
            INSERT INTO swings_new
                (id, symbol, swing_time, swing_price, swing_type, swing_class,
                 prior_opposite_swing_id, points_from_prior, candles_from_prior,
                 nearest_poi_event_id, candles_from_poi_event, created_at)
            SELECT
                id, symbol, swing_time, swing_price, swing_type, swing_class,
                prior_opposite_swing_id, points_from_prior, candles_from_prior,
                nearest_poi_event_id, candles_from_poi_event, created_at
            FROM swings
        """)
        rows_copied = cursor.rowcount
        print(f"[OK] Copied {rows_copied} swings to new table")

        # Step 3: Drop old table
        cursor.execute("DROP TABLE swings")
        print("[OK] Dropped old swings table")

        # Step 4: Rename new table
        cursor.execute("ALTER TABLE swings_new RENAME TO swings")
        print("[OK] Renamed new table to swings")

        conn.commit()
        print()
        print("[SUCCESS] Migration complete")
        print()

        # Verify the schema
        cursor.execute("PRAGMA table_info(swings)")
        columns = cursor.fetchall()

        print("Updated swings table schema:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")

        print(f"\nTotal columns: {len(columns)}")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration failed: {e}")
        raise

    finally:
        conn.close()


if __name__ == '__main__':
    print("="*80)
    print("Migration: Drop active_sessions_snapshot from swings table")
    print("="*80)
    print()
    migrate()
    print()
    print("[DONE]")
