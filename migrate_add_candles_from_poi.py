#!/usr/bin/env python3
"""
Migration: Add candles_from_poi_event column to swings table

This migration adds a new metric to track the temporal distance
between each swing and its linked POI event, measured in 1M candles.

This enables analysis of:
- How quickly swings form after POI events
- Timing patterns by swing class
- Relationship between POI proximity and swing significance
"""

import sqlite3

DB_PATH = 'data/ohlc_data.db'


def migrate():
    """Add candles_from_poi_event column to swings table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("Adding candles_from_poi_event column to swings table...")

        # Add the new column
        cursor.execute("""
            ALTER TABLE swings
            ADD COLUMN candles_from_poi_event INTEGER
        """)

        conn.commit()
        print("[OK] Column added successfully")

        # Verify the schema
        cursor.execute("PRAGMA table_info(swings)")
        columns = cursor.fetchall()

        print("\nUpdated swings table schema:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")

        print(f"\nTotal columns: {len(columns)}")

    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column already exists - migration skipped")
        else:
            raise

    finally:
        conn.close()


if __name__ == '__main__':
    print("="*80)
    print("Migration: Add candles_from_poi_event to swings table")
    print("="*80)
    print()
    migrate()
    print()
    print("[DONE] Migration complete")
