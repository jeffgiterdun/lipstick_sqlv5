#!/usr/bin/env python3
"""
Add incremental processing columns to sessions table.

These columns enable efficient incremental POI processing:
- last_poi_check_time: Track last time we scanned for POI touches (key for incremental POI processing)
- needs_recalc: Flag sessions that need recalculation (affected by new data)
- last_recalc_time: Track when session was last recalculated

This migration is SAFE to run multiple times (checks if columns exist first).
"""

import sqlite3

DB_PATH = 'data/ohlc_data.db'

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 80)
    print("MIGRATION: Add session tracking columns to sessions table")
    print("=" * 80)
    print()

    # Check current columns
    cursor.execute("PRAGMA table_info(sessions)")
    columns = [row[1] for row in cursor.fetchall()]

    print(f"Current sessions table has {len(columns)} columns")
    print()

    # Add last_poi_check_time column
    if 'last_poi_check_time' in columns:
        print("[SKIP] last_poi_check_time column already exists")
    else:
        print("Adding last_poi_check_time column...")
        cursor.execute("ALTER TABLE sessions ADD COLUMN last_poi_check_time TEXT")
        print("[OK] last_poi_check_time column added")

    # Add needs_recalc column
    if 'needs_recalc' in columns:
        print("[SKIP] needs_recalc column already exists")
    else:
        print("Adding needs_recalc column...")
        cursor.execute("ALTER TABLE sessions ADD COLUMN needs_recalc INTEGER DEFAULT 0")
        print("[OK] needs_recalc column added")

    # Add last_recalc_time column
    if 'last_recalc_time' in columns:
        print("[SKIP] last_recalc_time column already exists")
    else:
        print("Adding last_recalc_time column...")
        cursor.execute("ALTER TABLE sessions ADD COLUMN last_recalc_time TEXT")
        print("[OK] last_recalc_time column added")

    conn.commit()

    # Verify
    print()
    print("Verification:")
    print("-" * 80)

    cursor.execute("PRAGMA table_info(sessions)")
    columns = cursor.fetchall()
    print(f"Sessions table now has {len(columns)} columns")

    new_columns = ['last_poi_check_time', 'needs_recalc', 'last_recalc_time']
    print()
    print("New tracking columns:")
    for col in columns:
        col_name = col[1]
        col_type = col[2]
        if col_name in new_columns:
            print(f"  - {col_name} ({col_type})")

    print()
    print("=" * 80)
    print("[SUCCESS] Migration complete!")
    print("=" * 80)

    conn.close()

if __name__ == '__main__':
    migrate()
